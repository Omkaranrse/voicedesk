import asyncio
import re
import secrets

from livekit.agents import RunContext, function_tool
from pydantic import BaseModel, Field, ValidationError, field_validator

from . import db

VALID_DAYS = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}


def format_spoken_time(time_str: str) -> str:
    """Convert HH:MM (24-hour) to conversational 12-hour spoken format (e.g., '2:00 PM')."""
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", time_str.strip())
    if not match:
        return time_str
    h = int(match.group(1))
    m = match.group(2)
    meridiem = "AM" if h < 12 else "PM"
    h12 = 12 if h in (0, 12) else (h % 12)
    return f"{h12}:{m} {meridiem}"


def normalize_day(day: str) -> str:
    """Normalize spoken day descriptions (e.g. 'Monday morning', 'this Tuesday') to weekday name."""
    value = day.strip().lower()
    match = re.search(
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", value
    )
    if match:
        return match.group(1)
    return value


def normalize_time(time: str) -> str:
    """Normalize spoken and written time formats to HH:MM."""
    value = time.strip().lower().replace(".", "")

    # Strip phrases like "o'clock", "oclock", "o clock"
    value = re.sub(r"\bo['\s]?clock\b", "", value).strip()

    # Map colloquial dayparts to am/pm
    value = re.sub(r"\bin the morning\b", "am", value).strip()
    value = re.sub(r"\bin the (afternoon|evening)\b", "pm", value).strip()

    word_to_num = {
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "eleven": "11",
        "twelve": "12",
    }

    # Handle "half past <hour>"
    half_match = re.match(r"^half\s+past\s+([a-z0-9]+)\s*(am|pm)?$", value)
    if half_match:
        hour_part = half_match.group(1)
        meridiem_part = half_match.group(2) or ""
        hour_val = word_to_num.get(hour_part, hour_part)
        value = f"{hour_val}:30 {meridiem_part}".strip()

    # Standalone word replacements
    replacements = {
        "noon": "12:00",
        "midday": "12:00",
        "midnight": "00:00",
        "nine": "09:00",
        "ten": "10:00",
        "eleven": "11:00",
        "twelve": "12:00",
        "one": "13:00",
        "two": "14:00",
        "three": "15:00",
        "four": "16:00",
        "five": "17:00",
    }

    if value in replacements:
        return replacements[value]

    # Convert leading word numbers (e.g. "two pm", "ten am", "nine thirty")
    words = value.split()
    if words and words[0] in word_to_num:
        words[0] = word_to_num[words[0]]
        value = " ".join(words)

    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", value)
    if not match:
        return value

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)

    if minute > 59:
        return value

    if meridiem:
        if not 1 <= hour <= 12:
            return value
        if meridiem == "am" and hour == 12:
            hour = 0
        elif meridiem == "pm" and hour != 12:
            hour += 12
    elif hour > 23:
        return value
    elif 1 <= hour <= 5:
        hour += 12

    return f"{hour:02d}:{minute:02d}"


# --- Pydantic Validation Schemas ---


class CheckSlotsSchema(BaseModel):
    day: str = Field(..., description="Weekday name, e.g. 'monday'")

    @field_validator("day")
    @classmethod
    def validate_weekday(cls, v: str) -> str:
        norm = normalize_day(v)
        if norm not in VALID_DAYS:
            raise ValueError(f"'{v}' is not a recognized day of the week.")
        return norm


class LookupAppointmentSchema(BaseModel):
    day: str = Field(..., description="Weekday of the appointment")
    time: str = Field(..., description="Appointment time (e.g. '10:00 AM')")
    name: str = Field(
        ..., min_length=1, max_length=100, description="Caller's full name"
    )


class BookSlotSchema(BaseModel):
    day: str = Field(..., description="Weekday of the appointment")
    time: str = Field(..., description="Appointment time")
    name: str = Field(
        ..., min_length=1, max_length=100, description="Caller's full name"
    )


class CancelSlotSchema(BaseModel):
    day: str = Field(..., description="Weekday of the appointment")
    time: str = Field(..., description="Appointment time")
    name: str = Field(
        ..., min_length=1, max_length=100, description="Caller's full name"
    )
    verification_code: str = Field(
        ..., min_length=4, max_length=10, description="4-digit confirmation code"
    )


class RescheduleSlotSchema(BaseModel):
    old_day: str = Field(..., description="Current appointment day")
    old_time: str = Field(..., description="Current appointment time")
    new_day: str = Field(..., description="New appointment day")
    new_time: str = Field(..., description="New appointment time")
    name: str = Field(
        ..., min_length=1, max_length=100, description="Caller's full name"
    )
    verification_code: str = Field(
        ..., min_length=4, max_length=10, description="4-digit confirmation code"
    )


# --- Function Tools ---


@function_tool
async def check_slots(context: RunContext, day: str) -> str:
    """List free appointment times for a weekday such as 'monday'."""
    try:
        validated = CheckSlotsSchema(day=day)
    except ValidationError:
        return "Please specify a valid weekday such as Monday, Tuesday, or Wednesday."

    norm_day = validated.day
    slots = await asyncio.to_thread(db.free_slots, norm_day)
    if not slots:
        return f"No free slots on {norm_day}."
    spoken = [f"{s} ({format_spoken_time(s)})" for s in slots]
    return ", ".join(spoken)


@function_tool
async def lookup_appointment(
    context: RunContext,
    day: str,
    time: str,
    name: str,
) -> str:
    """Look up an existing appointment without making any changes.
    Separates inspection from mutation for caller privacy and safety.
    """
    try:
        validated = LookupAppointmentSchema(day=day, time=time, name=name)
    except ValidationError as err:
        return f"Invalid lookup parameters: {err.errors()[0]['msg']}."

    norm_day = normalize_day(validated.day)
    norm_time = normalize_time(validated.time)

    apt = await asyncio.to_thread(
        db.get_appointment, norm_day, norm_time, validated.name
    )
    if apt:
        spoken_time = format_spoken_time(norm_time)
        return f"Appointment confirmed for {validated.name} on {norm_day} at {norm_time} ({spoken_time})."

    return f"No appointment found for {validated.name} on {norm_day} at {format_spoken_time(norm_time)}."


@function_tool
async def book_slot(
    context: RunContext,
    day: str,
    time: str,
    name: str,
) -> str:
    """Book an appointment after the caller confirmed day, time and name.
    The slot must have been checked and verified available with check_slots first.
    Generates a secure 4-digit confirmation code for identity verification.
    """
    try:
        validated = BookSlotSchema(day=day, time=time, name=name)
    except ValidationError as err:
        return f"Invalid booking parameters: {err.errors()[0]['msg']}."

    norm_day = normalize_day(validated.day)
    normalized_time = normalize_time(validated.time)

    # Programmatic guardrail: ensure the slot is actually free before booking
    available_slots = await asyncio.to_thread(db.free_slots, norm_day)
    if normalized_time not in available_slots:
        spoken_avail = [f"{s} ({format_spoken_time(s)})" for s in available_slots]
        slots_str = ", ".join(spoken_avail) if spoken_avail else "no slots available"
        return f"Slot {normalized_time} on {norm_day} is not available. Available slots: {slots_str}."

    # Cryptographically secure 4-digit confirmation code
    pin = f"{secrets.randbelow(9000) + 1000}"

    booked = await asyncio.to_thread(
        db.book,
        norm_day,
        normalized_time,
        validated.name,
        pin,
    )

    if booked:
        spoken_time = format_spoken_time(normalized_time)
        return (
            f"Booked {validated.name} on {norm_day} at {normalized_time} ({spoken_time}). "
            f"Your confirmation code is {pin}."
        )

    return f"Slot {normalized_time} on {norm_day} is not available."


@function_tool
async def cancel_slot(
    context: RunContext,
    day: str,
    time: str,
    name: str,
    verification_code: str = "",
) -> str:
    """Cancel an existing appointment.
    Requires caller's name and 4-digit confirmation code to prevent unauthorized cancellation.
    """
    if not verification_code or not verification_code.strip():
        return (
            f"Identity verification required: please provide your 4-digit confirmation code "
            f"to cancel the appointment for {name}."
        )

    try:
        validated = CancelSlotSchema(
            day=day,
            time=time,
            name=name,
            verification_code=verification_code.strip(),
        )
    except ValidationError as err:
        return f"Verification error: {err.errors()[0]['msg']}."

    norm_day = normalize_day(validated.day)
    normalized_time = normalize_time(validated.time)

    # Verify appointment exists and verify confirmation code before mutation
    apt = await asyncio.to_thread(
        db.get_appointment, norm_day, normalized_time, validated.name
    )
    if not apt:
        spoken_time = format_spoken_time(normalized_time)
        return f"No appointment found for {validated.name} on {norm_day} at {normalized_time} ({spoken_time}) to cancel."

    if apt.get("pin") and apt["pin"] != validated.verification_code:
        return f"Identity verification failed: the confirmation code provided does not match the appointment for {validated.name}."

    cancelled = await asyncio.to_thread(
        db.cancel,
        norm_day,
        normalized_time,
        validated.name,
        validated.verification_code,
    )
    if cancelled:
        spoken_time = format_spoken_time(normalized_time)
        return f"Cancelled appointment for {validated.name} on {norm_day} at {normalized_time} ({spoken_time})."

    return f"Unable to cancel appointment for {validated.name} on {norm_day} at {normalized_time}."


@function_tool
async def reschedule_slot(
    context: RunContext,
    old_day: str,
    old_time: str,
    new_day: str,
    new_time: str,
    name: str,
    verification_code: str = "",
) -> str:
    """Reschedule an existing appointment to a new day and time.
    Requires caller's name and 4-digit confirmation code to prevent unauthorized modification.
    """
    if not verification_code or not verification_code.strip():
        return (
            f"Identity verification required: please provide your 4-digit confirmation code "
            f"to reschedule the appointment for {name}."
        )

    try:
        validated = RescheduleSlotSchema(
            old_day=old_day,
            old_time=old_time,
            new_day=new_day,
            new_time=new_time,
            name=name,
            verification_code=verification_code.strip(),
        )
    except ValidationError as err:
        return f"Verification error: {err.errors()[0]['msg']}."

    norm_old_day = normalize_day(validated.old_day)
    norm_old_time = normalize_time(validated.old_time)
    norm_new_day = normalize_day(validated.new_day)
    norm_new_time = normalize_time(validated.new_time)

    # 1. Verify target new slot availability
    available_new_slots = await asyncio.to_thread(db.free_slots, norm_new_day)
    if norm_new_time not in available_new_slots:
        spoken_avail = [f"{s} ({format_spoken_time(s)})" for s in available_new_slots]
        slots_str = ", ".join(spoken_avail) if spoken_avail else "no slots available"
        return (
            f"Cannot reschedule to {norm_new_day} at {norm_new_time} because it is not available. "
            f"Available slots: {slots_str}."
        )

    # 2. Verify original appointment exists and verify confirmation code
    apt = await asyncio.to_thread(
        db.get_appointment, norm_old_day, norm_old_time, validated.name
    )
    if not apt:
        return f"Unable to reschedule: no appointment found for {validated.name} on {norm_old_day} at {norm_old_time}."

    if apt.get("pin") and apt["pin"] != validated.verification_code:
        return f"Identity verification failed: the confirmation code provided does not match the appointment for {validated.name}."

    # 3. Execute atomic reschedule
    rescheduled = await asyncio.to_thread(
        db.reschedule,
        norm_old_day,
        norm_old_time,
        norm_new_day,
        norm_new_time,
        validated.name,
        validated.verification_code,
    )

    if rescheduled:
        spoken_new_time = format_spoken_time(norm_new_time)
        return (
            f"Rescheduled {validated.name} from {norm_old_day} at {norm_old_time} "
            f"to {norm_new_day} at {norm_new_time} ({spoken_new_time})."
        )

    return (
        f"Unable to reschedule {validated.name}. Target slot on {norm_new_day} at {norm_new_time} "
        f"is no longer available."
    )
