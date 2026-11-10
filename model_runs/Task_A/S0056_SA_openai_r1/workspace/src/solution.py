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
    """Accept a weekday name or a YYYY-MM-DD date for compatibility."""
    weekdays = {
        "monday", "tuesday", "wednesday", "thursday", "friday",
        "saturday", "sunday",
    }
    if isinstance(day, str) and day.strip().lower() in weekdays:
        return
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise ValueError(f"Invalid day: {day}")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return all minute-level starts within 09:00-17:00, excluding lunch.

    Lunch is 12:00-13:00. Intervals are half-open, so a meeting can end
    exactly when lunch or an event starts, or start exactly when one ends.
    Each returned start is an alternative, not an additional booked meeting.
    """
    validate_date(day)
    if not isinstance(meeting_duration, int) or isinstance(meeting_duration, bool):
        raise ValueError("Meeting duration must be a positive integer")
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    LUNCH_START = 12 * 60
    LUNCH_END = 13 * 60

    busy = []
    for e in events:
        if "start" not in e or "end" not in e:
            raise ValueError("Event must have 'start' and 'end'")
        s = time_to_minutes(e["start"])
        t = time_to_minutes(e["end"])
        if s >= t:
            raise ValueError(f"Invalid event interval: {e}")
        # Events wholly outside work do not block any suggestions. Retain
        # the in-hours portion of events that cross a working-hours boundary.
        start = max(s, WORK_START)
        end = min(t, WORK_END)
        if start < end:
            busy.append((start, end))

    busy.append((LUNCH_START, LUNCH_END))
    busy.sort()
    merged = []
    for s, e in busy:
        if not merged or merged[-1][1] < s:
            merged.append([s, e])
        else:
            merged[-1][1] = max(merged[-1][1], e)

    # Enumerate each free interval at the input's one-minute precision.
    slots = []
    free_start = WORK_START
    for busy_start, busy_end in merged:
        for start in range(free_start, busy_start - meeting_duration + 1):
            slots.append(minutes_to_time(start))
        free_start = busy_end
    for start in range(free_start, WORK_END - meeting_duration + 1):
        slots.append(minutes_to_time(start))
    return slots
