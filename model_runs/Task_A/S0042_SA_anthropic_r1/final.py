from typing import List, Dict
from datetime import datetime

WORK_START = 9 * 60
WORK_END = 17 * 60
LUNCH_START = 12 * 60
LUNCH_END = 13 * 60
BUFFER = 15
GRANULARITY = 15

DAY_ABBRS = {"mo", "tu", "we", "th", "fr", "sa", "su"}


def to_minutes(t: str) -> int:
    """Parse a 24-hour 'HH:MM' string (AM/PM formats are rejected)."""
    try:
        h, m = map(int, t.split(":"))
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError
        return h * 60 + m
    except Exception:
        raise ValueError(f"Invalid time format: {t}")


def to_time_str(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def merge_intervals(intervals):
    intervals.sort()
    merged = []

    for start, end in intervals:
        if not merged or merged[-1][1] < start:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    return merged


def _validate_day(day) -> None:
    if isinstance(day, str) and day.strip().lower() in DAY_ABBRS:
        return
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except Exception:
        raise ValueError(f"Invalid day: {day}")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # Validate inputs
    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int):
        raise ValueError("Meeting duration must be an integer number of minutes")
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")
    _validate_day(day)

    # Step 1: convert events + apply buffer after each event
    blocked = []
    for e in events:
        start = to_minutes(e["start"])
        end = to_minutes(e["end"])
        if start >= end:
            raise ValueError(f"Event start must be before end: {e}")
        blocked.append((start, end + BUFFER))

    # Step 2: lunch break
    blocked.append((LUNCH_START, LUNCH_END))

    # Step 3: merge overlaps
    blocked = merge_intervals(blocked)

    # Step 4: find available gaps (all within working hours)
    slots = []
    current = WORK_START

    for start, end in blocked:
        if current < start:
            gap_end = min(start, WORK_END)
            t = current
            while t + meeting_duration <= gap_end:
                slots.append(to_time_str(t))
                t += GRANULARITY
        current = max(current, end)

    # last gap after final blocked interval
    if current < WORK_END:
        t = current
        while t + meeting_duration <= WORK_END:
            slots.append(to_time_str(t))
            t += GRANULARITY

    return sorted(slots)
