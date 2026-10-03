from unittest.mock import MagicMock

from livekit.agents import MetricsCollectedEvent, metrics

from voicedesk.config import settings
from voicedesk.metrics import attach_metrics


def test_privacy_default_setting():
    """Verify that transcript logging is disabled by default."""
    assert settings.log_transcripts is False


def test_metrics_do_not_store_transcripts(tmp_path, monkeypatch):
    """Verify that performance metrics collected do NOT contain spoken transcript text."""
    metrics_file = tmp_path / "metrics.csv"
    monkeypatch.setattr(settings, "metrics_csv", str(metrics_file))

    mock_session = MagicMock()
    registered_handlers = {}

    def mock_on(event_name):
        def decorator(fn):
            registered_handlers[event_name] = fn
            return fn

        return decorator

    mock_session.on = mock_on
    attach_metrics(mock_session, "privacy-room-test")

    handler = registered_handlers["metrics_collected"]

    # Emit STT metrics
    stt_m = metrics.STTMetrics(
        timestamp=100.0,
        request_id="req-stt-1",
        duration=0.25,
        audio_duration=1.2,
        streamed=False,
        label="test-stt",
    )
    handler(MetricsCollectedEvent(metrics=stt_m))

    # Emit LLM metrics
    llm_m = metrics.LLMMetrics(
        timestamp=101.0,
        request_id="req-llm-1",
        ttft=0.45,
        duration=0.9,
        cancelled=False,
        label="test-llm",
        completion_tokens=15,
        prompt_tokens=25,
        prompt_cached_tokens=0,
        total_tokens=40,
        tokens_per_second=16.6,
    )
    handler(MetricsCollectedEvent(metrics=llm_m))

    # Check metrics CSV content
    content = metrics_file.read_text()
    assert "stt" in content
    assert "llm" in content
    # Ensure no spoken text or prompt text is anywhere in the file
    assert "Hello" not in content
    assert "appointment" not in content
