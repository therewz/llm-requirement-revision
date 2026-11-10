from typing import List, Dict, Optional

WORK_START = 9 * 60
WORK_END = 17 * 60
LUNCH_START = 12 * 60
LUNCH_END = 13 * 60
SLOT_GRANULARITY = 15


def time_to_minutes(t: str) -> int:
    """Convert 'HH:MM' string to minutes since midnight."""
    if not isinstance(t, str):
        raise ValueError(f"Invalid time format: {t!r}")
    try:
        h, m = map(int, t.strip().split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except Exception:
        raise ValueError(f"Invalid time format: {t!r}")
    return h * 60 + m


def minutes_to_time(m: int) -> str:
    """Convert minutes since midnight to 'HH:MM' string."""
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}"


def suggest_slots(events: List[Dict[str, str]], meeting_duration, day: Optional[str] = None) -> List[str]:
    """Return valid meeting start times ('HH:MM'), in 15-minute increments.

    events: list of dicts with key "start" ("HH:MM") and optionally "end".
            An event without "end" occupies the 15-minute slot beginning at its start.
            Events outside working hours (09:00-17:00) are rejected (ValueError).
    meeting_duration: minutes (int or integer string).
    day: accepted for compatibility; not used.
    """
    # Input validation
    if not isinstance(events, list):
        raise ValueError("Events must be a list")
    try:
        duration = int(str(meeting_duration).strip())
    except ValueError:
        raise ValueError("Meeting duration must be an integer number of minutes")
    if duration <= 0:
        raise ValueError("Meeting duration must be positive")

    intervals = []
    for ev in events:
        if not isinstance(ev, dict) or "start" not in ev:
            raise ValueError("Each event must be a dict with a 'start' key")
        start = time_to_minutes(ev["start"])
        if ev.get("end") is not None:
            end = time_to_minutes(ev["end"])
        else:
            end = start + SLOT_GRANULARITY
        if start < WORK_START or end > WORK_END:
            raise ValueError(f"Event outside working hours: {ev}")
        if start >= end:
            raise ValueError(f"Invalid event interval: {ev}")
        intervals.append((start, end))

    slots = []
    for current in range(WORK_START, WORK_END - duration + 1, SLOT_GRANULARITY):
        if LUNCH_START <= current < LUNCH_END:
            continue
        end = current + duration
        if any(current < e and end > s for s, e in intervals):
            continue
        slots.append(minutes_to_time(current))

    print(slots)
    return slots
