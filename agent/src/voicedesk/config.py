from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamically locate .env file from common project run paths
_CANDIDATE_ENV_PATHS = [
    Path(".env"),
    Path("../.env"),
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]
_RESOLVED_ENV_PATH = next((str(p) for p in _CANDIDATE_ENV_PATHS if p.is_file()), ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_RESOLVED_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    stt_provider: str = "openai"  # "openai" (Speaches/Whisper) or "deepgram"
    stt_base_url: str = "http://localhost:8000/v1"
    stt_model: str = "Systran/faster-whisper-small"
    deepgram_api_key: str = ""

    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "llama3.2:3b"
    llm_api_key: str = "not-needed"

    fallback_llm_base_url: str = ""
    fallback_llm_model: str = ""
    fallback_llm_api_key: str = ""

    tts_base_url: str = "http://localhost:8880/v1"
    tts_model: str = "kokoro"
    tts_voice: str = "af_alloy"

    max_call_duration_seconds: int = 300
    log_transcripts: bool = False
    num_idle_processes: int = 2
    preemptive_tts: bool = True
    max_context_items: int = 14

    db_path: str = "voicedesk.db"
    metrics_csv: str = "../benchmarks/results/metrics.csv"


settings = Settings()
