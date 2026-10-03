import asyncio
import csv
import logging
import time
from pathlib import Path
from typing import Any

from livekit.agents import MetricsCollectedEvent, metrics

from .config import settings

logger = logging.getLogger("voicedesk.metrics")

_metrics_queue: asyncio.Queue[list[Any] | None] | None = None
_writer_task: asyncio.Task | None = None


def _write_row_sync(row: list[Any]) -> None:
    """Synchronous file write executed in a background worker thread."""
    try:
        path = Path(settings.metrics_csv)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
    except (OSError, csv.Error) as exc:
        logger.warning(
            "Failed to append metrics row to %s: %s", settings.metrics_csv, exc
        )


async def _background_writer():
    """Background worker draining metrics queue without blocking the main event loop."""
    assert _metrics_queue is not None
    while True:
        try:
            row = await _metrics_queue.get()
            if row is None:
                _metrics_queue.task_done()
                break
            await asyncio.to_thread(_write_row_sync, row)
            _metrics_queue.task_done()
        except asyncio.CancelledError:
            # Drain any remaining rows on cancellation
            while not _metrics_queue.empty():
                try:
                    remaining = _metrics_queue.get_nowait()
                    if remaining is not None:
                        _write_row_sync(remaining)
                        _metrics_queue.task_done()
                except (asyncio.QueueEmpty, OSError):
                    break
            raise
        except Exception as exc:  # noqa: BLE001 - resilience against telemetry failure
            logger.warning("Error in metrics background worker: %s", exc)


def _ensure_background_writer():
    global _metrics_queue, _writer_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        if _metrics_queue is None:
            _metrics_queue = asyncio.Queue()
        if _writer_task is None or _writer_task.done():
            _writer_task = asyncio.create_task(
                _background_writer(), name="voicedesk.metrics_writer"
            )


def attach_metrics(session, room: str):
    _ensure_background_writer()

    @session.on("metrics_collected")
    def _on(ev: MetricsCollectedEvent):
        m = ev.metrics

        metrics.log_metrics(m)

        if isinstance(m, metrics.LLMMetrics):
            row = [
                time.time(),
                room,
                "llm",
                m.ttft,
            ]

        elif isinstance(m, metrics.TTSMetrics):
            row = [
                time.time(),
                room,
                "tts",
                m.ttfb,
                m.duration,
                m.audio_duration,
                m.acquire_time,
                m.connection_reused,
                m.cancelled,
                m.characters_count,
            ]

        elif isinstance(m, metrics.EOUMetrics):
            row = [
                time.time(),
                room,
                "eou",
                m.end_of_utterance_delay,
            ]

        elif isinstance(m, metrics.STTMetrics):
            row = [
                time.time(),
                room,
                "stt",
                m.duration,
            ]

        else:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running() and _metrics_queue is not None:
            _metrics_queue.put_nowait(row)
        else:
            # Synchronous direct write fallback (e.g. In unit tests without running event loop)
            _write_row_sync(row)

    if hasattr(session, "on"):
        try:
            session.on("close", lambda *_: None)
        except Exception as exc:  # noqa: BLE001 - safety check on mock sessions
            logger.debug("Failed to register close listener: %s", exc)
