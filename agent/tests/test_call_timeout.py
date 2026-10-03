import asyncio
from unittest.mock import AsyncMock, MagicMock

from voicedesk.config import settings
from voicedesk.main import _enforce_call_duration_cap


def test_default_call_duration_setting():
    """Verify that default call duration limit is 300 seconds (5 minutes)."""
    assert settings.max_call_duration_seconds == 300


def test_call_duration_cap_triggers_disconnect():
    """Verify that the supervisor announces timeout and cleanly disconnects when timer expires."""

    async def _test():
        mock_session = MagicMock()
        mock_speech_handle = asyncio.Future()
        mock_speech_handle.set_result(None)
        mock_session.say.return_value = mock_speech_handle

        mock_ctx = MagicMock()
        mock_ctx.room.name = "test-room-123"
        mock_ctx.room.disconnect = AsyncMock()

        # Run with a short 0.05s timeout
        await _enforce_call_duration_cap(
            session=mock_session,
            ctx=mock_ctx,
            max_duration=0.05,
        )

        # Verify announcement was made
        mock_session.say.assert_called_once_with(
            "Sorry, we've reached the maximum call time. Goodbye.",
            allow_interruptions=False,
        )

        # Verify room was disconnected cleanly
        mock_ctx.room.disconnect.assert_awaited_once()

    asyncio.run(_test())


def test_call_duration_cap_clean_cancellation():
    """Verify that cancelling the supervisor before timeout does not crash or raise."""

    async def _test():
        mock_session = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.room.name = "test-room-cancel"
        mock_ctx.room.disconnect = AsyncMock()

        task = asyncio.create_task(
            _enforce_call_duration_cap(
                session=mock_session,
                ctx=mock_ctx,
                max_duration=10.0,
            )
        )

        await asyncio.sleep(0.02)
        task.cancel()

        # Should finish without raising CancelledError to caller
        await task
        mock_ctx.room.disconnect.assert_not_called()

    asyncio.run(_test())
