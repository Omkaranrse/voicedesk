import asyncio
import re
import sqlite3
from unittest.mock import MagicMock

from voicedesk import db
from voicedesk.config import settings
from voicedesk.tools import (
    book_slot,
    cancel_slot,
    check_slots,
    lookup_appointment,
    reschedule_slot,
)


def test_appointment_identity_verification_lifecycle(tmp_path, monkeypatch):
    """Verify that cancellation and rescheduling strictly require confirmation code verification."""

    async def _test():
        monkeypatch.setattr(settings, "db_path", str(tmp_path / "test_sec.db"))
        db.init_db()
        ctx = MagicMock()

        # 1. Book slot for Bob
        res = await book_slot(ctx, "monday", "10:00", "Bob")
        assert "Booked Bob" in res
        assert "confirmation code is" in res

        # Extract 4-digit PIN
        pin_match = re.search(r"confirmation code is (\d{4})", res)
        assert pin_match is not None
        pin = pin_match.group(1)

        # 2. Lookup appointment without mutating
        lookup_res = await lookup_appointment(ctx, "monday", "10:00", "Bob")
        assert "Appointment confirmed for Bob on monday at 10:00" in lookup_res

        # 3. Unverified rescheduling without code must fail
        unauth_resched = await reschedule_slot(
            ctx,
            old_day="monday",
            old_time="10:00",
            new_day="tuesday",
            new_time="11:00",
            name="Bob",
            verification_code="",
        )
        assert "Identity verification required" in unauth_resched
        assert "10:00" not in await check_slots(ctx, "monday")

        # 4. Rescheduling with valid code succeeds
        valid_resched = await reschedule_slot(
            ctx,
            old_day="monday",
            old_time="10:00",
            new_day="tuesday",
            new_time="11:00",
            name="Bob",
            verification_code=pin,
        )
        assert "Rescheduled Bob" in valid_resched
        assert "10:00" in await check_slots(ctx, "monday")
        assert "11:00" not in await check_slots(ctx, "tuesday")

        # 5. Unverified cancellation without code must fail
        unauth_cancel = await cancel_slot(
            ctx, "tuesday", "11:00", "Bob", verification_code=""
        )
        assert "Identity verification required" in unauth_cancel
        assert "11:00" not in await check_slots(ctx, "tuesday")

        # 6. Cancellation with wrong code must fail
        wrong_code_cancel = await cancel_slot(
            ctx, "tuesday", "11:00", "Bob", verification_code="9999"
        )
        assert "Identity verification failed" in wrong_code_cancel
        assert "11:00" not in await check_slots(ctx, "tuesday")

        # 7. Cancellation with correct code succeeds
        valid_cancel = await cancel_slot(
            ctx, "tuesday", "11:00", "Bob", verification_code=pin
        )
        assert "Cancelled appointment for Bob" in valid_cancel
        assert "11:00" in await check_slots(ctx, "tuesday")

    asyncio.run(_test())


def test_input_validation_boundaries(tmp_path, monkeypatch):
    """Verify Pydantic input models reject invalid days and times gracefully."""

    async def _test():
        monkeypatch.setattr(settings, "db_path", str(tmp_path / "test_val.db"))
        db.init_db()
        ctx = MagicMock()

        # Invalid day input
        invalid_day_res = await check_slots(ctx, "not-a-real-day")
        assert "Please specify a valid weekday" in invalid_day_res

        # Empty name in booking
        invalid_booking = await book_slot(ctx, "monday", "10:00", "")
        assert "Invalid booking parameters" in invalid_booking

    asyncio.run(_test())


def test_db_retry_on_lock(tmp_path, monkeypatch):
    """Verify _retry_on_lock retries and succeeds if lock clears within budget."""
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "test_lock.db"))
    attempts = 0

    def flaky_db_op():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise sqlite3.OperationalError("database is locked")
        return "success"

    result = db._retry_on_lock(flaky_db_op, max_retries=3, initial_delay=0.01)
    assert result == "success"
    assert attempts == 2
