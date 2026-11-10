from typing import List, Tuple, Union, Dict
from datetime import datetime

_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


def suggest_slots(events, meeting_duration: int, day: str) -> List[str]:
    """
    Suggest valid meeting start times for a given day.

    Args:
        events: List of events, each a (start, end) pair of "HH:MM" strings
                (dicts with 'start' and 'end' keys are also accepted).
        meeting_duration (int): Meeting duration in minutes (positive int).
        day (str): Three-letter day string, e.g. "Mon".

    Returns:
        List[str]: Valid start times in "HH:MM" format, ascending.
    """
    # --- Input validation ---
    if not isinstance(day, str):
        raise ValueError("Invalid day")
    if day.strip().lower()[:3] not in _DAYS:
        # Also tolerate a full date string
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid day")

    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive integer")

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    LUNCH_START = 12 * 60
    LUNCH_END = 13 * 60
    STEP = 15

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
    blocked = []

    for e in events:
        if isinstance(e, dict):
            s, en = e["start"], e["end"]
        else:
            s, en = e
        start = to_minutes(s)
        end = to_minutes(en)
        if start >= end:
            raise ValueError(f"Event start >= end: {e}")

        # Events entirely outside working hours are ignored
        if end <= WORK_START or start >= WORK_END:
            continue

        blocked.append((max(start, WORK_START), min(end, WORK_END)))

    # Lunch break
    blocked.append((LUNCH_START, LUNCH_END))

    # --- Determine candidate slots ---
    slots = []
    current = WORK_START
    latest_start = WORK_END - meeting_duration

    while current <= latest_start:
        slot_end = current + meeting_duration
        if all(slot_end <= b_start or current >= b_end for b_start, b_end in blocked):
            slots.append(to_time_str(current))
        current += STEP

    return slots
