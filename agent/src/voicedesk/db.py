import logging
import sqlite3
import time
from collections.abc import Callable
from typing import Any

from .config import settings

logger = logging.getLogger("voicedesk.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def _retry_on_lock(
    func: Callable[[], Any], max_retries: int = 3, initial_delay: float = 0.05
) -> Any:
    """Execute a database operation with bounded retry and backoff on database locks."""
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return func()
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower() and attempt < max_retries - 1:
                logger.warning(
                    "Database locked on attempt %d/%d; retrying in %.2fs",
                    attempt + 1,
                    max_retries,
                    delay,
                )
                time.sleep(delay)
                delay *= 2
            else:
                raise


def init_db():
    def _op():
        with _conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS slots(
                    day TEXT,
                    time TEXT,
                    booked_by TEXT,
                    pin TEXT,
                    PRIMARY KEY(day, time)
                )
                """
            )
            # Ensure pin column exists for schema migrations
            cols = [r[1] for r in c.execute("PRAGMA table_info(slots)").fetchall()]
            if "pin" not in cols:
                c.execute("ALTER TABLE slots ADD COLUMN pin TEXT")

            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_slots_free ON slots(day, booked_by)"
            )

            if c.execute("SELECT COUNT(*) FROM slots").fetchone()[0] == 0:
                c.executemany(
                    "INSERT INTO slots(day, time) VALUES(?, ?)",
                    [
                        (d, t)
                        for d in ("monday", "tuesday", "wednesday")
                        for t in ("10:00", "11:00", "14:00")
                    ],
                )

    _retry_on_lock(_op)


def free_slots(day: str) -> list[str]:
    def _op():
        with _conn() as c:
            rows = c.execute(
                """
                SELECT time
                FROM slots
                WHERE day=? AND booked_by IS NULL
                ORDER BY time
                """,
                (day.lower(),),
            )
            return [r[0] for r in rows]

    return _retry_on_lock(_op)


def get_appointment(day: str, time: str, name: str) -> dict | None:
    """Read-only lookup to separate appointment inspection from mutation."""

    def _op():
        with _conn() as c:
            row = c.execute(
                """
                SELECT day, time, booked_by, pin
                FROM slots
                WHERE day=? AND time=? AND (LOWER(booked_by)=LOWER(?) OR booked_by=?)
                """,
                (day.lower(), time, name.strip(), name.strip()),
            ).fetchone()
            if row:
                return {
                    "day": row[0],
                    "time": row[1],
                    "booked_by": row[2],
                    "pin": row[3],
                }
            return None

    return _retry_on_lock(_op)


def book(day: str, time: str, name: str, pin: str | None = None) -> bool:
    def _op():
        with _conn() as c:
            cur = c.execute(
                """
                UPDATE slots
                SET booked_by=?, pin=?
                WHERE day=? AND time=? AND booked_by IS NULL
                """,
                (name.strip(), pin.strip() if pin else None, day.lower(), time),
            )
            return cur.rowcount == 1

    return _retry_on_lock(_op)


def cancel(day: str, time: str, name: str, pin: str | None = None) -> bool:
    def _op():
        with _conn() as c:
            if pin is not None and pin.strip():
                cur = c.execute(
                    """
                    UPDATE slots
                    SET booked_by=NULL, pin=NULL
                    WHERE day=? AND time=? AND (LOWER(booked_by)=LOWER(?) OR booked_by=?) AND (pin=? OR pin IS NULL)
                    """,
                    (day.lower(), time, name.strip(), name.strip(), pin.strip()),
                )
            else:
                cur = c.execute(
                    """
                    UPDATE slots
                    SET booked_by=NULL, pin=NULL
                    WHERE day=? AND time=? AND (LOWER(booked_by)=LOWER(?) OR booked_by=?)
                    """,
                    (day.lower(), time, name.strip(), name.strip()),
                )
            return cur.rowcount == 1

    return _retry_on_lock(_op)


def reschedule(
    old_day: str,
    old_time: str,
    new_day: str,
    new_time: str,
    name: str,
    pin: str | None = None,
) -> bool:
    def _op():
        with _conn() as conn, conn:
            # Atomic transaction block (BEGIN IMMEDIATE ... COMMIT / ROLLBACK)
            cur = conn.cursor()
            if pin is not None and pin.strip():
                existing = cur.execute(
                    """
                    SELECT booked_by, pin FROM slots
                    WHERE day=? AND time=? AND (LOWER(booked_by)=LOWER(?) OR booked_by=?) AND (pin=? OR pin IS NULL)
                    """,
                    (
                        old_day.lower(),
                        old_time,
                        name.strip(),
                        name.strip(),
                        pin.strip(),
                    ),
                ).fetchone()
            else:
                existing = cur.execute(
                    """
                    SELECT booked_by, pin FROM slots
                    WHERE day=? AND time=? AND (LOWER(booked_by)=LOWER(?) OR booked_by=?)
                    """,
                    (old_day.lower(), old_time, name.strip(), name.strip()),
                ).fetchone()

            if not existing:
                return False

            saved_pin = existing[1] or (pin.strip() if pin else None)

            # 1. Release old slot
            cur.execute(
                """
                UPDATE slots
                SET booked_by=NULL, pin=NULL
                WHERE day=? AND time=?
                """,
                (old_day.lower(), old_time),
            )

            # 2. Book new slot
            cur.execute(
                """
                UPDATE slots
                SET booked_by=?, pin=?
                WHERE day=? AND time=? AND booked_by IS NULL
                """,
                (name.strip(), saved_pin, new_day.lower(), new_time),
            )

            if cur.rowcount != 1:
                # Transaction context manager rolls back on exception
                raise sqlite3.IntegrityError("Target slot is unavailable")

            return True

    try:
        return _retry_on_lock(_op)
    except sqlite3.IntegrityError:
        return False
