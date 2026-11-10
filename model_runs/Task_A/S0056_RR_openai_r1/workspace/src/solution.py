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


def _day_of_week(day: str) -> int:
    """Resolve a weekday name or an existing YYYY-MM-DD date input."""
    weekdays = (
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday",
    )
    normalized = day.strip().lower()
    for index, name in enumerate(weekdays):
        if normalized in (name, name[:3]):
            return index
    try:
        return datetime.strptime(day, "%Y-%m-%d").weekday()
    except ValueError:
        raise ValueError(f"Invalid day: {day}") from None


def validate_date(day: str):
    """Ensure the day string is a valid weekday name or date."""
    _day_of_week(day)


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return every valid minute-level start between 09:00 and 17:00.

    Meetings must avoid lunch (12:00-13:00) and existing events. On
    Fridays, starts are additionally limited to 15:00 or earlier.
    Returned starts are alternatives, not a set of meetings to book together.
    """
    day_of_week = _day_of_week(day)
    if not isinstance(meeting_duration, int) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be a positive integer")

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    LUNCH_START = 12 * 60
    LUNCH_END = 13 * 60
    FRIDAY_LAST_START = 15 * 60

    # Clip events to working hours; wholly external events cannot conflict.
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

    # Merging makes event ordering and overlapping busy intervals immaterial.
    busy.sort()
    merged = []
    for s, e in busy:
        if not merged or merged[-1][1] < s:
            merged.append([s, e])
        else:
            merged[-1][1] = max(merged[-1][1], e)

    max_start_time = WORK_END - meeting_duration
    if day_of_week == 4:
        max_start_time = min(max_start_time, FRIDAY_LAST_START)

    slots = []
    for start in range(WORK_START, max_start_time + 1):
        end = start + meeting_duration
        # Adjacent meetings are allowed; only actual overlap is a conflict.
        if all(end <= s or start >= e for s, e in merged):
            slots.append(minutes_to_time(start))

    return slots
