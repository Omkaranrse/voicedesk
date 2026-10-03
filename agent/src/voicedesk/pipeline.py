import logging

from livekit.agents import AgentSession, TurnHandlingOptions, llm, stt
from livekit.agents.voice.agent_session import SessionConnectOptions
from livekit.agents.voice.transcription.text_transforms import replace
from livekit.plugins import openai

from .config import settings as s
from .kokoro_tts import KokoroTTS
from .resilient_llm import ResilientLLM

logger = logging.getLogger("voicedesk.pipeline")


def _build_stt() -> stt.STT:
    """Build STT engine based on configured provider."""
    if s.stt_provider.lower() == "deepgram" and s.deepgram_api_key:
        try:
            from livekit.plugins import deepgram

            logger.info("Initializing Deepgram streaming STT provider")
            return deepgram.STT(api_key=s.deepgram_api_key)
        except ImportError:
            logger.warning(
                "livekit-plugins-deepgram not installed; falling back to Speaches OpenAI STT"
            )

    # Default: Speaches faster-whisper over OpenAI endpoint
    return openai.STT(
        model=s.stt_model,
        base_url=s.stt_base_url,
        api_key="not-needed",
        language="en",
        temperature=0.0,
        prompt="VoiceDesk clinic receptionist. Appointments, Monday, Tuesday, Wednesday, 10:00 AM, 11:00 AM, 2:00 PM.",
    )


def build_session(vad) -> AgentSession:
    primary = openai.LLM(
        model=s.llm_model,
        base_url=s.llm_base_url,
        api_key=s.llm_api_key,
    )

    models: list[llm.LLM] = [primary]

    if s.fallback_llm_base_url:
        backup = openai.LLM(
            model=s.fallback_llm_model,
            base_url=s.fallback_llm_base_url,
            api_key=s.fallback_llm_api_key,
        )
        models.append(backup)

    # FallbackAdapter tries primary first, then backup if primary fails
    adapter = llm.FallbackAdapter(
        models,
        attempt_timeout=5.0,
        max_retry_per_llm=0,
    )

    # ResilientLLM catches any remaining exceptions and enforces bounded context window
    chat_llm = ResilientLLM(
        underlying=adapter,
        recovery_message="Sorry, give me a moment.",
        max_context_items=s.max_context_items,
    )

    return AgentSession(
        conn_options=SessionConnectOptions(max_unrecoverable_errors=100),
        vad=vad,
        turn_handling=TurnHandlingOptions(
            turn_detection="vad",
            endpointing={"mode": "fixed", "min_delay": 0.6, "max_delay": 1.4},
            preemptive_generation={"enabled": True, "preemptive_tts": s.preemptive_tts},
        ),
        tts_text_transforms=[
            replace(
                {
                    "10:00": "10:00 AM",
                    "11:00": "11:00 AM",
                    "14:00": "2:00 PM",
                    "12:00": "12:00 PM",
                    "09:00": "9:00 AM",
                    "13:00": "1:00 PM",
                    "15:00": "3:00 PM",
                    "16:00": "4:00 PM",
                    "17:00": "5:00 PM",
                }
            ),
            "filter_markdown",
            "filter_emoji",
        ],
        stt=_build_stt(),
        llm=chat_llm,
        tts=KokoroTTS(
            base_url=s.tts_base_url,
            model=s.tts_model,
            voice=s.tts_voice,
        ),
    )
