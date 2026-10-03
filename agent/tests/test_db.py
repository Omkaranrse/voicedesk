from voicedesk import db
from voicedesk.config import settings


def test_no_double_booking(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "t.db"))

    db.init_db()

    assert db.book("monday", "10:00", "Asha") is True
    assert db.book("monday", "10:00", "Ravi") is False
    assert "10:00" not in db.free_slots("monday")


def test_db_cancel_and_reschedule(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "t_resched.db"))

    db.init_db()

    # Initial booking
    assert db.book("monday", "10:00", "David") is True

    # Reschedule to free Tuesday slot
    assert db.reschedule("monday", "10:00", "tuesday", "11:00", "David") is True
    assert "10:00" in db.free_slots("monday")
    assert "11:00" not in db.free_slots("tuesday")

    # Reschedule to already booked slot must fail and keep current state
    assert db.book("wednesday", "14:00", "Sarah") is True
    assert db.reschedule("tuesday", "11:00", "wednesday", "14:00", "David") is False
    assert "11:00" not in db.free_slots("tuesday")

    # Cancel Tuesday slot
    assert db.cancel("tuesday", "11:00", "David") is True
    assert "11:00" in db.free_slots("tuesday")
