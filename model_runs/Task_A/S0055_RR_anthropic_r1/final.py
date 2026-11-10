from typing import List, Dict, Union
from datetime import datetime


def time_to_minutes(t: str) -> int:
    """Convert 'HH:MM' string to minutes since midnight."""
    try:
        if not isinstance(t, str):
            raise ValueError
        h, m = map(int, t.strip().split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except Exception:
        raise ValueError(f"Invalid time format: {t}")
    return h * 60 + m


def minutes_to_time(m: int) -> str:
    """Convert minutes since midnight to 'HH:MM' string."""
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}"


def validate_date(day: str):
    """Validate date string 'YYYY-MM-DD'."""
    try:
        return datetime.strptime(day, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise ValueError(f"Invalid date: {day}")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: Union[int, str], day: str) -> List[str]:
    # -----------------------------
    # 1. Input validation
    # -----------------------------
    dt = validate_date(day)

    try:
        meeting_duration = int(meeting_duration)
    except (ValueError, TypeError):
        raise ValueError("Meeting duration must be an integer number of minutes")
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    if not isinstance(events, list):
        raise ValueError("Events must be a list")

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    LUNCH_START = 12 * 60
    LUNCH_END = 13 * 60
    SLOT_GRANULARITY = 15
    FRIDAY_CUTOFF = 15 * 60  # Friday meetings must not start after 15:00

    # -----------------------------
    # 2. Normalize events (order-independent)
    # -----------------------------
    normalized_events = []
    for ev in events:
        if not isinstance(ev, dict) or "start" not in ev:
            raise ValueError("Event must be a dict with a 'start' key")
        start = time_to_minutes(ev["start"])
        if ev.get("end") is not None:
            end = time_to_minutes(ev["end"])
        else:
            end = start + SLOT_GRANULARITY  # no end given: occupies one slot
        if start >= end:
            raise ValueError(f"Invalid event interval: {ev}")
        if start < WORK_START or end > WORK_END:
            raise ValueError(f"Event outside working hours: {ev}")
        normalized_events.append((start, end))

    # -----------------------------
    # 3. Generate valid start times
    # -----------------------------
    is_friday = dt.weekday() == 4
    slots = []
    current = WORK_START
    while current + meeting_duration <= WORK_END:
        if is_friday and current > FRIDAY_CUTOFF:
            break

        # No meeting may start during lunch
        if LUNCH_START <= current < LUNCH_END:
            current = LUNCH_END
            continue

        conflict = any(current < e and current + meeting_duration > s
                       for s, e in normalized_events)
        if not conflict:
            slots.append(minutes_to_time(current))

        current += SLOT_GRANULARITY

    print(slots)
    return slots
