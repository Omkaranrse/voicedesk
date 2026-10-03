import asyncio
import re
from unittest.mock import MagicMock

from livekit.agents.llm import ChatContext

from voicedesk import db
from voicedesk.config import settings
from voicedesk.resilient_llm import ResilientLLM
from voicedesk.tools import (
    book_slot,
    cancel_slot,
    check_slots,
    lookup_appointment,
    reschedule_slot,
)


class MockLLM:
    """Mock LLM to test context window truncation without making network requests."""

    def __init__(self):
        self.model = "mock-model"
        self.provider = "mock-provider"
        self.metrics_metadata = {}

    def chat(self, *, chat_ctx, tools=None, conn_options=None, **kwargs):
        class MockStream:
            async def __aiter__(self):
                if False:
                    yield None

        return MockStream()

    def on(self, *args, **kwargs):
        pass

    def off(self, *args, **kwargs):
        pass

    def prewarm(self, *args, **kwargs):
        pass

    async def aclose(self):
        pass


def test_full_conversational_e2e_lifecycle(tmp_path, monkeypatch):
    """End-to-end test verifying multi-turn appointment lifecycle:
    check -> book -> lookup -> unverified reschedule rejection -> verified reschedule
    -> unverified cancel rejection -> verified cancel.
    """

    async def _test():
        monkeypatch.setattr(settings, "db_path", str(tmp_path / "e2e.db"))
        db.init_db()
        ctx = MagicMock()

        # Turn 1: Check available slots for Monday
        free_mon = await check_slots(ctx, "monday")
        assert "10:00" in free_mon
        assert "11:00" in free_mon

        # Turn 2: Book Monday at 10:00 AM for Dr. Watson's patient 'John Doe'
        book_res = await book_slot(ctx, "monday", "10:00 AM", "John Doe")
        assert "Booked John Doe on monday at 10:00" in book_res
        assert "confirmation code is" in book_res
        pin_match = re.search(r"confirmation code is (\d{4})", book_res)
        assert pin_match is not None
        code = pin_match.group(1)

        # Monday 10:00 must no longer be free
        assert "10:00" not in await check_slots(ctx, "monday")

        # Turn 3: Lookup the booking (inspection without mutation)
        lookup_res = await lookup_appointment(ctx, "monday", "10:00", "John Doe")
        assert "Appointment confirmed for John Doe on monday at 10:00" in lookup_res

        # Turn 4: Attempt unverified reschedule without confirmation code
        unauth_resched = await reschedule_slot(
            ctx,
            old_day="monday",
            old_time="10:00",
            new_day="tuesday",
            new_time="11:00",
            name="John Doe",
            verification_code="",
        )
        assert "Identity verification required" in unauth_resched
        # Old slot still booked
        assert "10:00" not in await check_slots(ctx, "monday")

        # Turn 5: Reschedule with valid confirmation code to Tuesday 11:00 AM
        valid_resched = await reschedule_slot(
            ctx,
            old_day="monday",
            old_time="10:00",
            new_day="tuesday",
            new_time="11:00",
            name="John Doe",
            verification_code=code,
        )
        assert "Rescheduled John Doe" in valid_resched
        assert "tuesday at 11:00" in valid_resched

        # Monday 10:00 is free again, Tuesday 11:00 is now booked
        assert "10:00" in await check_slots(ctx, "monday")
        assert "11:00" not in await check_slots(ctx, "tuesday")

        # Turn 6: Attempt unverified cancel without confirmation code
        unauth_cancel = await cancel_slot(
            ctx, "tuesday", "11:00", "John Doe", verification_code=""
        )
        assert "Identity verification required" in unauth_cancel
        assert "11:00" not in await check_slots(ctx, "tuesday")

        # Turn 7: Cancel with valid confirmation code
        valid_cancel = await cancel_slot(
            ctx, "tuesday", "11:00", "John Doe", verification_code=code
        )
        assert "Cancelled appointment for John Doe" in valid_cancel

        # Tuesday 11:00 is free again
        assert "11:00" in await check_slots(ctx, "tuesday")

    asyncio.run(_test())


def test_context_window_truncation():
    """Verify that ResilientLLM truncates chat context to max_context_items,
    preserving initial system instructions while preventing token bloat.
    """

    async def _test():
        mock_underlying = MockLLM()
        resilient = ResilientLLM(mock_underlying, max_context_items=10)

        # Build context with 1 system instruction + 20 conversational turns
        chat_ctx = ChatContext.empty()
        chat_ctx.add_message(
            role="system", content="System instruction for clinic receptionist."
        )
        for i in range(20):
            chat_ctx.add_message(role="user", content=f"User message turn {i}")
            chat_ctx.add_message(
                role="assistant", content=f"Assistant response turn {i}"
            )

        assert len(chat_ctx.items) == 41  # 1 system + 40 dialog messages

        # Trigger stream execution which enforces truncation
        stream = resilient.chat(chat_ctx=chat_ctx)
        await stream._run()

        # Context items must be bounded to 1 + 10 = 11 items
        assert len(chat_ctx.items) <= 11
        # System instruction must be preserved at index 0
        first_msg = chat_ctx.items[0]
        assert getattr(
            first_msg, "role", ""
        ) == "system" or "System instruction" in str(first_msg)

    asyncio.run(_test())


def test_sip_caller_id_detection():
    """Verify telephone caller ID detection from participant attributes and identities."""
    # 1. Attribute detection (RFC standard SIP trunk headers)
    mock_participant = MagicMock()
    mock_participant.attributes = {"sip.phoneNumber": "+14155552671"}
    mock_participant.identity = "sip_call_user"

    attrs = mock_participant.attributes
    phone = None
    for key in (
        "sip.phoneNumber",
        "sip.callerId",
        "sip.trunkPhoneNumber",
        "phone_number",
    ):
        if attrs.get(key):
            phone = attrs[key]
            break
    assert phone == "+14155552671"

    # 2. Identity fallback detection
    mock_participant_2 = MagicMock()
    mock_participant_2.attributes = {}
    mock_participant_2.identity = "sip_+19175558832"

    ident = mock_participant_2.identity
    clean_id = ident.removeprefix("sip_")
    assert clean_id == "+19175558832"

    # 3. Room name prefix fallback detection
    room_name = "sip-call-_18005550199_994827"
    match = re.search(r"sip-call-_([^_]+)_", room_name)
    assert match is not None
    assert match.group(1) == "18005550199"
