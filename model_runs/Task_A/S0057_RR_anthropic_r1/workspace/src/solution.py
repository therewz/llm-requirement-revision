from typing import List, Dict
from datetime import datetime

_DAY_ABBREVS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # -----------------------------
    # Validation
    # -----------------------------
    if not isinstance(day, str):
        raise ValueError("Day must be a string")

    weekday = None
    if len(day) == 3 and day.isalpha():
        if day.lower() not in _DAY_ABBREVS:
            raise ValueError("Invalid day. Use a 3-letter day such as 'Fri'")
        weekday = _DAY_ABBREVS.index(day.lower())
    else:
        # Also accept an ISO date (YYYY-MM-DD) for compatibility
        try:
            weekday = datetime.strptime(day, "%Y-%m-%d").weekday()
        except (ValueError, TypeError):
            raise ValueError("Day must be a 3-letter string such as 'Fri'")

    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be greater than 0")

    # -----------------------------
    # Helpers
    # -----------------------------
    def to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
            return h * 60 + m
        except Exception:
            raise ValueError("Invalid time format")

    def to_str(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    # -----------------------------
    # Constants
    # -----------------------------
    WORK_START = 9 * 60
    WORK_END = 17 * 60
    FRIDAY_LATEST_START = 15 * 60
    STEP = 15

    latest_start = WORK_END - meeting_duration
    if weekday == 4:
        latest_start = min(latest_start, FRIDAY_LATEST_START)

    # -----------------------------
    # Normalize events
    # -----------------------------
    intervals = []
    for e in events:
        start = to_minutes(e["start"])
        end = to_minutes(e["end"])

        if start >= end:
            raise ValueError("Invalid event interval")

        intervals.append((start, end))

    intervals.sort()

    # -----------------------------
    # Generate slots (15-min increments)
    # -----------------------------
    result = []
    current = WORK_START
    while current <= latest_start:
        end = current + meeting_duration
        if all(end <= s or current >= e for s, e in intervals):
            result.append(to_str(current))
        current += STEP

    return result
