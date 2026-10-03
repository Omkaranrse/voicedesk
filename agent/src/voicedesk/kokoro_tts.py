from __future__ import annotations

import asyncio
import logging
import re
import time

import httpx
from livekit.agents import tts, utils
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

logger = logging.getLogger("voicedesk.kokoro_tts")

# Common abbreviations that end in a dot but do not denote sentence boundaries
ABBREVIATIONS = {"dr", "mr", "mrs", "ms", "prof", "vs", "etc", "eg", "ie"}


def split_sentences_stream(text: str, is_final: bool = False) -> tuple[list[str], str]:
    """
    Split incoming streaming text into sentence or clause chunks suitable for Kokoro TTS.

    Guarantees:
    - Does not split inside times (e.g., '10:00', '11:30') or decimal numbers.
    - Does not split on common abbreviations when followed by lowercase.
    - Yields complete sentences immediately when sentence termination punctuation (. ? !) is found.
    - For clauses without terminal punctuation (>= 28 chars), splits on comma/semicolon/colon if present to stream audio early.
    - Enforces a minimum chunk length (>= 12 chars) unless is_final=True to avoid tiny fragments.
    """
    sentences: list[str] = []
    buffer = text

    while buffer:
        # Check for sentence end (. ? ! or newline)
        m = re.search(r"([.?!]+|\n)(?:\s+|$)", buffer)

        # If no sentence end, check if buffer is long enough (>= 28 chars) and has a clause break (, or ;)
        if not m and len(buffer) >= 28:
            m = re.search(r"([,;])(?:\s+)", buffer)

        if not m:
            break

        punct = m.group(1)
        end_pos = m.end()
        candidate = buffer[: m.start() + len(punct)].strip()
        remaining = buffer[end_pos:]

        words = candidate.split()
        last_word = words[-1].lower().rstrip(".?!,;") if words else ""

        # Avoid splitting on known abbreviations if followed by lowercase
        if last_word in ABBREVIATIONS and remaining and remaining[0].islower():
            match_start = m.start() + 1
            sub_m = re.search(r"([.?!]+|\n)(?:\s+|$)", buffer[match_start:])
            if sub_m:
                m = sub_m
                punct = m.group(1)
                end_pos = match_start + m.end()
                candidate = buffer[: match_start + m.start() + len(punct)].strip()
            else:
                break

        # Check minimum length (12 chars) to prevent tiny fragments
        if len(candidate) >= 12 or is_final:
            sentences.append(candidate)
            buffer = buffer[end_pos:].lstrip()
        else:
            break

    if is_final and buffer.strip():
        sentences.append(buffer.strip())
        buffer = ""

    return sentences, buffer


class KokoroChunkedStream(tts.ChunkedStream):
    """Isolated/standalone synthesis stream for single-shot calls."""

    def __init__(
        self,
        *,
        tts_instance: KokoroTTS,
        input_text: str,
        conn_options: APIConnectOptions,
    ):
        super().__init__(
            tts=tts_instance, input_text=input_text, conn_options=conn_options
        )
        self._tts = tts_instance

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        output_emitter.initialize(
            request_id=utils.shortuuid(),
            sample_rate=self._tts.sample_rate,
            num_channels=self._tts.num_channels,
            mime_type="audio/pcm",
            stream=False,
        )
        self._connection_reused = True
        self._acquire_time = 0.001

        client = await self._tts._get_client()
        t_req = time.perf_counter()
        first_chunk = True

        async with client.stream(
            "POST",
            "/audio/speech",
            json={
                "model": self._tts._model,
                "input": self.input_text,
                "voice": self._tts._voice,
                "response_format": "pcm",
                "stream": True,
            },
            timeout=httpx.Timeout(30.0, connect=self._conn_options.timeout),
        ) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes():
                if first_chunk:
                    logger.debug(
                        "Kokoro direct chunk TTFB: %.3fs for %d chars",
                        time.perf_counter() - t_req,
                        len(self.input_text),
                    )
                    first_chunk = False
                output_emitter.push(chunk)

        output_emitter.flush()


class KokoroSynthesizeStream(tts.SynthesizeStream):
    """Streaming synthesizer that converts streaming LLM tokens into sentence audio."""

    def __init__(
        self,
        *,
        tts_instance: KokoroTTS,
        conn_options: APIConnectOptions,
    ):
        super().__init__(tts=tts_instance, conn_options=conn_options)
        self._tts = tts_instance
        self._t_created = time.perf_counter()
        self._t_first_token: float | None = None
        self._t_first_sent_queued: float | None = None
        self._t_first_byte: float | None = None

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        request_id = utils.shortuuid()
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=self._tts.sample_rate,
            num_channels=self._tts.num_channels,
            mime_type="audio/pcm",
            stream=True,
        )
        segment_id = utils.shortuuid()
        output_emitter.start_segment(segment_id=segment_id)

        queue: asyncio.Queue[str | None] = asyncio.Queue()
        buffer = ""

        async def forward_input():
            nonlocal buffer
            async for token in self._input_ch:
                if self._t_first_token is None:
                    self._t_first_token = time.perf_counter()

                if isinstance(token, self._FlushSentinel):
                    sents, buffer = split_sentences_stream(buffer, is_final=True)
                    for s in sents:
                        if self._t_first_sent_queued is None:
                            self._t_first_sent_queued = time.perf_counter()
                        await queue.put(s)
                    continue

                buffer += token
                sents, buffer = split_sentences_stream(buffer, is_final=False)
                for s in sents:
                    if self._t_first_sent_queued is None:
                        self._t_first_sent_queued = time.perf_counter()
                    await queue.put(s)

            # Flush any remaining text on stream completion
            sents, buffer = split_sentences_stream(buffer, is_final=True)
            for s in sents:
                if self._t_first_sent_queued is None:
                    self._t_first_sent_queued = time.perf_counter()
                await queue.put(s)

            await queue.put(None)

        async def synthesize_worker():
            self._connection_reused = True
            self._acquire_time = 0.001
            client = await self._tts._get_client()

            while True:
                sentence = await queue.get()
                if sentence is None:
                    break

                self._mark_started()
                t_req_start = time.perf_counter()
                first_byte_in_sent = True

                try:
                    async with client.stream(
                        "POST",
                        "/audio/speech",
                        json={
                            "model": self._tts._model,
                            "input": sentence,
                            "voice": self._tts._voice,
                            "response_format": "pcm",
                            "stream": True,
                        },
                        timeout=httpx.Timeout(30.0, connect=self._conn_options.timeout),
                    ) as resp:
                        resp.raise_for_status()
                        async for chunk in resp.aiter_bytes():
                            if first_byte_in_sent:
                                now = time.perf_counter()
                                if self._t_first_byte is None:
                                    self._t_first_byte = now
                                    logger.info(
                                        "TTS Pipeline Timings: token_to_first_sent=%.3fs, "
                                        "req_to_first_byte=%.3fs, overall_ttfb=%.3fs (chars=%d)",
                                        (self._t_first_sent_queued or now)
                                        - (self._t_first_token or self._t_created),
                                        now - t_req_start,
                                        now - self._t_created,
                                        len(sentence),
                                    )
                                first_byte_in_sent = False
                            output_emitter.push(chunk)

                    output_emitter.flush()
                except asyncio.CancelledError:
                    logger.debug("TTS synthesis worker cancelled during HTTP stream")
                    raise

        tasks = [
            asyncio.create_task(forward_input(), name="KokoroTTS.forward_input"),
            asyncio.create_task(
                synthesize_worker(), name="KokoroTTS.synthesize_worker"
            ),
        ]

        try:
            await asyncio.gather(*tasks)
        finally:
            await utils.aio.cancel_and_wait(*tasks)


class KokoroTTS(tts.TTS):
    """
    High-performance native LiveKit TTS adapter for Kokoro FastAPI.

    Optimizations:
    - streaming=True: Bypasses LiveKit's default StreamAdapter and its lookahead buffering.
    - Sentence/clause accumulator: Sends complete sentences to Kokoro immediately without
      waiting for subsequent sentences or full LLM completion.
    - Direct PCM: Uses raw 24kHz 16-bit PCM (response_format='pcm') directly with AudioEmitter,
      avoiding WAV header overhead and FFmpeg decoding.
    - Persistent HTTP client: Reuses TCP connections and keep-alive across turns.
    - Cancellation safety: Cancels in-flight Kokoro synthesis immediately on user interruption.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:8880/v1",
        model: str = "kokoro",
        voice: str = "af_alloy",
        sample_rate: int = 24000,
        client: httpx.AsyncClient | None = None,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=True, aligned_transcript=False),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._voice = voice
        self._client = client
        self._owns_client = client is None

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        return "kokoro"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=20,
                    keepalive_expiry=120,
                ),
            )
        return self._client

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> KokoroChunkedStream:
        return KokoroChunkedStream(
            tts_instance=self, input_text=text, conn_options=conn_options
        )

    def stream(
        self, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> KokoroSynthesizeStream:
        return KokoroSynthesizeStream(tts_instance=self, conn_options=conn_options)

    async def aclose(self) -> None:
        if self._owns_client and self._client and not self._client.is_closed:
            await self._client.aclose()
