import asyncio
from unittest.mock import MagicMock

from voicedesk import db
from voicedesk.agent import INSTRUCTIONS
from voicedesk.config import settings
from voicedesk.tools import book_slot, check_slots, normalize_time


def test_time_normalization_formats():
    """Verify all required time normalization formats."""
    assert normalize_time("11") == "11:00"
    assert normalize_time("11:30 am") == "11:30"
    assert normalize_time("11:00 am") == "11:00"
    assert normalize_time("2 pm") == "14:00"
    assert normalize_time("2:30 pm") == "14:30"
    assert normalize_time("12 am") == "00:00"
    assert normalize_time("12 pm") == "12:00"


def test_prompt_guardrails_contain_critical_rules():
    """Verify system instructions enforce strict booking and anti-hallucination rules."""
    assert "Never invent appointment times" in INSTRUCTIONS
    assert "check_slots" in INSTRUCTIONS
    assert "book_slot" in INSTRUCTIONS
    assert "day" in INSTRUCTIONS.lower()
    assert "time" in INSTRUCTIONS.lower()
    assert "name" in INSTRUCTIONS.lower()
    assert "unavailable" in INSTRUCTIONS.lower()
    # Check adversarial instructions mention
    assert "bypass" in INSTRUCTIONS.lower() or "assume" in INSTRUCTIONS.lower()


def test_slot_availability_guardrail(tmp_path, monkeypatch):
    """Test programmatic slot checking and booking guardrails."""

    async def _test():
        test_db = str(tmp_path / "test_slots.db")
        monkeypatch.setattr(settings, "db_path", test_db)
        db.init_db()

        mock_context = MagicMock()

        # 1. Check free slots for Monday
        slots_result = await check_slots(mock_context, "monday")
        assert "10:00" in slots_result

        # 2. Book an available slot
        book_result = await book_slot(mock_context, "monday", "10:00", "Asha")
        assert "Booked Asha on monday at 10:00" in book_result

        # 3. Attempting to book the SAME slot again must fail and list available slots
        duplicate_result = await book_slot(mock_context, "monday", "10:00", "Ravi")
        assert "is not available" in duplicate_result

        # 4. Attempting to book an invalid or non-existent slot without checking must fail
        invalid_result = await book_slot(mock_context, "monday", "5 pm", "Eve")
        assert "is not available" in invalid_result

    asyncio.run(_test())
