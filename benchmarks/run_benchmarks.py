import asyncio
import statistics
import sys
import time
from pathlib import Path

import httpx

# Ensure agent/src is available on sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agent" / "src"))

from voicedesk.kokoro_tts import KokoroTTS

TEST_SENTENCES = [
    "Hello, this is VoiceDesk clinic. How can I help you today?",
    "Available slots on Monday are 10:00, 11:00, and 14:00.",
    "Would you like me to book one of those slots for you?",
    "Before booking, please confirm the day, time, and your name.",
    "I have booked your appointment for John on Wednesday at 11:00 am.",
]


def benchmark_direct_kokoro():
    print("--- 1. Direct Kokoro Benchmark (5 requests) ---")
    durations = []

    try:
        with httpx.Client(base_url="http://localhost:8880/v1", timeout=10.0) as client:
            for i, sent in enumerate(TEST_SENTENCES, 1):
                t0 = time.perf_counter()
                try:
                    resp = client.post(
                        "/audio/speech",
                        json={
                            "model": "kokoro",
                            "input": sent,
                            "voice": "af_alloy",
                            "response_format": "pcm",
                            "stream": True,
                        },
                    )
                    resp.raise_for_status()
                    first_byte_time = None
                    for _ in resp.iter_bytes():
                        if first_byte_time is None:
                            first_byte_time = time.perf_counter() - t0
                    total_time = time.perf_counter() - t0
                    durations.append(first_byte_time or total_time)
                    print(
                        f"  Req {i} ({len(sent)} chars): TTFB={first_byte_time:.3f}s, Total={total_time:.3f}s"
                    )
                except httpx.HTTPError as err:
                    print(f"  Req {i} failed: {err}")

        if durations:
            avg = sum(durations) / len(durations)
            print(
                f"Direct Kokoro: Avg={avg:.3f}s, Min={min(durations):.3f}s, Max={max(durations):.3f}s\n"
            )
        else:
            print("Direct Kokoro: No successful responses (service may be offline or restricted).\n")
    except httpx.HTTPError as exc:
        print(f"Direct Kokoro connection failed: {exc}\n")

    return durations


async def benchmark_isolated_livekit_tts():
    print("--- 2. Isolated LiveKit KokoroTTS Adapter Benchmark (5 requests) ---")
    tts_inst = KokoroTTS(base_url="http://localhost:8880/v1")
    durations = []

    try:
        for i, sent in enumerate(TEST_SENTENCES, 1):
            t0 = time.perf_counter()
            first_frame_time = None
            total_audio = 0.0
            try:
                stream = tts_inst.synthesize(sent)
                async for audio in stream:
                    if first_frame_time is None:
                        first_frame_time = time.perf_counter() - t0
                    total_audio += audio.frame.duration
                total_time = time.perf_counter() - t0
                durations.append(first_frame_time or total_time)
                print(
                    f"  Req {i} ({len(sent)} chars): TTFB={first_frame_time:.3f}s, "
                    f"Total={total_time:.3f}s, Audio={total_audio:.3f}s"
                )
            except (httpx.HTTPError, OSError) as err:
                print(f"  Req {i} failed: {err}")

        if durations:
            avg = sum(durations) / len(durations)
            print(
                f"LiveKit KokoroTTS Adapter: Avg={avg:.3f}s, Min={min(durations):.3f}s, Max={max(durations):.3f}s\n"
            )
        else:
            print("LiveKit KokoroTTS: No successful synthesis streams.\n")
    finally:
        await tts_inst.aclose()

    return durations


async def _run_single_concurrent_request(client: httpx.AsyncClient, text: str) -> dict:
    t0 = time.perf_counter()
    first_byte = None
    bytes_count = 0
    try:
        async with client.stream(
            "POST",
            "/audio/speech",
            json={
                "model": "kokoro",
                "input": text,
                "voice": "af_alloy",
                "response_format": "pcm",
                "stream": True,
            },
            timeout=15.0,
        ) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes():
                if first_byte is None:
                    first_byte = time.perf_counter() - t0
                bytes_count += len(chunk)
        total = time.perf_counter() - t0
        return {
            "success": True,
            "ttfb": first_byte or total,
            "total": total,
            "bytes": bytes_count,
        }
    except (httpx.HTTPError, OSError) as exc:
        return {
            "success": False,
            "error": str(exc),
            "ttfb": None,
            "total": time.perf_counter() - t0,
        }


async def benchmark_concurrent_load(concurrency_levels: list[int] = (1, 5, 10)):
    print("--- 3. Multi-Session Concurrent Load Benchmark ---")
    try:
        async with httpx.AsyncClient(base_url="http://localhost:8880/v1") as client:
            for concurrency in concurrency_levels:
                print(f"\n[Testing Concurrency = {concurrency} Simultaneous Sessions]")
                tasks = [
                    _run_single_concurrent_request(
                        client, TEST_SENTENCES[i % len(TEST_SENTENCES)]
                    )
                    for i in range(concurrency)
                ]
                t_start = time.perf_counter()
                results = await asyncio.gather(*tasks)
                elapsed = time.perf_counter() - t_start

                successful = [r for r in results if r["success"] and r["ttfb"] is not None]
                failures = [r for r in results if not r["success"]]
                ttfbs = [r["ttfb"] for r in successful]

                if ttfbs:
                    p50 = statistics.median(ttfbs)
                    p95 = (
                        statistics.quantiles(ttfbs, n=20)[18]
                        if len(ttfbs) > 1
                        else ttfbs[0]
                    )
                    print(
                        f"  Concurrency {concurrency:2d}: Success={len(successful)}/{concurrency}, "
                        f"WallTime={elapsed:.2f}s, TTFB p50={p50:.3f}s, TTFB p95={p95:.3f}s, Failures={len(failures)}"
                    )
                else:
                    print(
                        f"  Concurrency {concurrency:2d}: 0/{concurrency} successful. "
                        f"Errors: {failures[0]['error'] if failures else 'unknown'}"
                    )
    except (httpx.HTTPError, OSError) as exc:
        print(f"Concurrent load benchmark connection failed: {exc}")


def main():
    benchmark_direct_kokoro()
    asyncio.run(benchmark_isolated_livekit_tts())
    asyncio.run(benchmark_concurrent_load([1, 5, 10]))


if __name__ == "__main__":
    main()
