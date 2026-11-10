from typing import List, Dict
from datetime import datetime

_DAY_ABBR = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """
    Suggest valid meeting start times for a given day.

    Args:
        events: List of events with 'start' and 'end' in HH:MM format.
        meeting_duration: Meeting duration in minutes (positive int).
        day: Three-letter day string (e.g. "Mon"); a YYYY-MM-DD date is also accepted.

    Returns:
        Valid start times in HH:MM format, ascending.
    """
    # --- Input validation ---
    if not isinstance(day, str):
        raise ValueError("Invalid day")
    key = day.strip().lower()
    if key[:3] in _DAY_ABBR and len(key) == 3:
        weekday = _DAY_ABBR[key]
    else:
        try:
            weekday = datetime.strptime(day, "%Y-%m-%d").weekday()
        except ValueError:
            raise ValueError("Invalid day")

    if (not isinstance(meeting_duration, int) or isinstance(meeting_duration, bool)
            or meeting_duration <= 0):
        raise ValueError("Meeting duration must be positive integer")

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    LUNCH_START = 12 * 60
    LUNCH_END = 13 * 60
    STEP = 15
    FRIDAY_LATEST_START = 15 * 60

    def to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            return h * 60 + m
        except Exception:
            raise ValueError(f"Invalid time format: {t}")

    def to_time_str(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    # --- Build blocked intervals ---
    blocked = [(LUNCH_START, LUNCH_END)]

    for e in events:
        start = to_minutes(e["start"])
        end = to_minutes(e["end"])
        if start >= end:
            raise ValueError(f"Event start >= end: {e}")

        # Events outside working hours are ignored
        if end <= WORK_START or start >= WORK_END:
            continue

        blocked.append((max(start, WORK_START), min(end, WORK_END)))

    # --- Determine candidate slots ---
    latest_start = WORK_END - meeting_duration
    if weekday == 4:  # Friday: no meeting may start after 15:00
        latest_start = min(latest_start, FRIDAY_LATEST_START)

    slots = []
    current = WORK_START
    while current <= latest_start:
        slot_end = current + meeting_duration
        if all(slot_end <= b_start or current >= b_end for b_start, b_end in blocked):
            slots.append(to_time_str(current))
        current += STEP

    return slots
