import asyncio
import re
from unittest.mock import MagicMock

from voicedesk import db
from voicedesk.config import settings
from voicedesk.tools import (
    book_slot,
    cancel_slot,
    check_slots,
    lookup_appointment,
    normalize_day,
    normalize_time,
    reschedule_slot,
)


def test_normalize_time_required_formats():
    assert normalize_time("11") == "11:00"
    assert normalize_time("11:30 am") == "11:30"
    assert normalize_time("11:00 am") == "11:00"
    assert normalize_time("2 pm") == "14:00"
    assert normalize_time("2:30 pm") == "14:30"
    assert normalize_time("12 am") == "00:00"
    assert normalize_time("12 pm") == "12:00"


def test_normalize_time_extended_spoken_formats():
    # Word numbers
    assert normalize_time("nine") == "09:00"
    assert normalize_time("ten") == "10:00"
    assert normalize_time("eleven") == "11:00"
    assert normalize_time("twelve") == "12:00"
    assert normalize_time("one") == "13:00"
    assert normalize_time("two") == "14:00"
    assert normalize_time("three") == "15:00"
    assert normalize_time("four") == "16:00"
    assert normalize_time("five") == "17:00"

    # Natural phrases
    assert normalize_time("10 o'clock") == "10:00"
    assert normalize_time("half past ten") == "10:30"
    assert normalize_time("noon") == "12:00"
    assert normalize_time("midday") == "12:00"

    # Unspaced indicators
    assert normalize_time("10am") == "10:00"
    assert normalize_time("2pm") == "14:00"
    assert normalize_time("11:30am") == "11:30"


def test_normalize_day():
    assert normalize_day("monday") == "monday"
    assert normalize_day("Monday morning") == "monday"
    assert normalize_day("this coming Tuesday afternoon") == "tuesday"
    assert normalize_day("Wednesday") == "wednesday"
    assert normalize_day("Thursday evening") == "thursday"
    assert normalize_day("Friday") == "friday"


def test_cancel_and_reschedule_slots(tmp_path, monkeypatch):
    async def _test():
        monkeypatch.setattr(settings, "db_path", str(tmp_path / "test_ops.db"))
        db.init_db()
        mock_ctx = MagicMock()

        # 1. Book Monday 10:00
        book_res = await book_slot(mock_ctx, "Monday morning", "10 o'clock", "Alice")
        assert "Booked Alice on monday at 10:00" in book_res
        assert "confirmation code is" in book_res
        pin_match = re.search(r"confirmation code is (\d+)", book_res)
        assert pin_match is not None
        pin = pin_match.group(1)

        # 2. Lookup appointment
        lookup_res = await lookup_appointment(mock_ctx, "monday", "10:00", "Alice")
        assert "Appointment confirmed for Alice on monday at 10:00" in lookup_res

        # 3. Security: Attempting to reschedule without PIN must be rejected
        unauth_resched = await reschedule_slot(
            mock_ctx,
            old_day="Monday",
            old_time="10:00",
            new_day="Tuesday morning",
            new_time="11am",
            name="Alice",
            verification_code="",
        )
        assert "Identity verification required" in unauth_resched

        # 4. Security: Attempting to reschedule with wrong PIN must be rejected
        wrong_resched = await reschedule_slot(
            mock_ctx,
            old_day="Monday",
            old_time="10:00",
            new_day="Tuesday morning",
            new_time="11am",
            name="Alice",
            verification_code="9999" if pin != "9999" else "8888",
        )
        assert "Identity verification failed" in wrong_resched

        # 5. Authorized reschedule with valid PIN
        resched_res = await reschedule_slot(
            mock_ctx,
            old_day="Monday",
            old_time="10:00",
            new_day="Tuesday morning",
            new_time="11am",
            name="Alice",
            verification_code=pin,
        )
        assert "Rescheduled Alice" in resched_res
        assert "tuesday at 11:00" in resched_res

        # Monday 10:00 should be free again
        free_mon = await check_slots(mock_ctx, "monday")
        assert "10:00" in free_mon

        # 6. Security: Attempting to cancel without PIN must be rejected
        unauth_cancel = await cancel_slot(
            mock_ctx, "Tuesday", "11:00", "Alice", verification_code=""
        )
        assert "Identity verification required" in unauth_cancel

        # 7. Security: Attempting to cancel with wrong PIN must be rejected
        wrong_cancel = await cancel_slot(
            mock_ctx,
            "Tuesday",
            "11:00",
            "Alice",
            verification_code="0000" if pin != "0000" else "1111",
        )
        assert "Identity verification failed" in wrong_cancel

        # 8. Authorized cancel with valid PIN
        cancel_res = await cancel_slot(
            mock_ctx, "Tuesday", "11:00", "Alice", verification_code=pin
        )
        assert "Cancelled appointment for Alice on tuesday at 11:00" in cancel_res

        # Tuesday 11:00 should now be free
        free_tue = await check_slots(mock_ctx, "tuesday")
        assert "11:00" in free_tue

    asyncio.run(_test())
