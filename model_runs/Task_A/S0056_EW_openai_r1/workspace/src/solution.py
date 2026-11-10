from typing import List, Dict
from datetime import datetime


def time_to_minutes(t: str) -> int:
    """Convert HH:MM string to minutes since midnight."""
    try:
        h, m = map(int, t.split(":"))
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError
        return h * 60 + m
    except Exception:
        raise ValueError(f"Invalid time format: {t}")


def minutes_to_time(m: int) -> str:
    """Convert minutes since midnight to HH:MM string."""
    h = m // 60
    m = m % 60
    return f"{h:02d}:{m:02d}"


def validate_date(day: str):
    """Accept a weekday name or, for compatibility, an ISO date."""
    if isinstance(day, str) and day.strip().lower() in (
        "monday", "tuesday", "wednesday", "thursday", "friday",
        "saturday", "sunday",
    ):
        return
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise ValueError(f"Invalid date: {day}")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return every minute-resolution start that fits within the working day.

    Slots are alternatives, not a set of meetings to book together. Existing
    events and lunch occupy half-open intervals, so back-to-back meetings are
    allowed.
    """
    validate_date(day)
    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int):
        raise ValueError("Meeting duration must be an integer number of minutes")
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    LUNCH_START = 12 * 60
    LUNCH_END = 13 * 60

    # Convert events to busy intervals, ignoring portions outside working hours.
    busy = []
    for e in events:
        if "start" not in e or "end" not in e:
            raise ValueError("Event must have 'start' and 'end'")
        s = time_to_minutes(e["start"])
        t = time_to_minutes(e["end"])
        if s >= t:
            raise ValueError(f"Invalid event interval: {e}")
        start = max(s, WORK_START)
        end = min(t, WORK_END)
        if start < end:
            busy.append((start, end))

    busy.append((LUNCH_START, LUNCH_END))

    # Sorting and merging makes results independent of input order and handles
    # overlapping or adjacent existing events.
    busy.sort()
    merged = []
    for s, e in busy:
        if not merged or merged[-1][1] < s:
            merged.append([s, e])
        else:
            merged[-1][1] = max(merged[-1][1], e)

    slots = []
    for t in range(WORK_START, WORK_END - meeting_duration + 1):
        slot_end = t + meeting_duration
        if all(slot_end <= s or t >= e for s, e in merged):
            slots.append(minutes_to_time(t))

    return slots
