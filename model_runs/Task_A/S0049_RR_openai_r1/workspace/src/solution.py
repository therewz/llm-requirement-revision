"""Suggest meeting start times within working hours, avoiding blocked periods."""
from typing import List, Dict
from datetime import date

WORK_START = 9 * 60
WORK_END = 19 * 60
LUNCH_START = 12 * 60
LUNCH_END = 13 * 60
SLOT_STEP = 15
FRIDAY_LATEST_START = 15 * 60


def _to_minutes(time_str: str) -> int:
    hours, minutes = time_str.split(":")
    return int(hours) * 60 + int(minutes)


def _to_hhmm(total_minutes: int) -> str:
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def _merge_intervals(intervals: List[tuple[int, int]]) -> List[tuple[int, int]]:
    if not intervals:
        return []

    intervals.sort()
    merged: List[tuple[int, int]] = [intervals[0]]
    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _is_friday(day: str) -> bool:
    normalized = day.strip()
    if normalized[:3].lower() == "fri":
        return True

    try:
        return date.fromisoformat(normalized).weekday() == 4
    except ValueError:
        return False


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
        meeting_duration: Positive integer meeting length in minutes
        day: Day label/date string (e.g., "Fri" or "2026-02-06")

    Returns:
        List of valid start times as "HH:MM" sorted ascending. Meetings fit
        within 09:00-19:00, avoid lunch and events (with a 15-minute cooldown),
        and start no later than 15:00 on Fridays.
    """
    if (
        isinstance(meeting_duration, bool)
        or not isinstance(meeting_duration, int)
        or meeting_duration <= 0
    ):
        return []

    busy_intervals: List[tuple[int, int]] = []
    for event in events:
        start = _to_minutes(event["start"])
        end = _to_minutes(event["end"])
        if end <= start or end <= WORK_START or start >= WORK_END:
            continue

        clipped_start = max(start, WORK_START)
        # Keep a 15-minute cooldown after each in-hours calendar event.
        clipped_end = min(end + SLOT_STEP, WORK_END)
        if clipped_start < clipped_end:
            busy_intervals.append((clipped_start, clipped_end))

    busy_intervals.append((LUNCH_START, LUNCH_END))
    busy_intervals = _merge_intervals(busy_intervals)

    slots: List[str] = []
    meeting_end_limit = WORK_END

    is_friday = _is_friday(day)

    for start in range(WORK_START, WORK_END + 1, SLOT_STEP):
        end = start + meeting_duration
        if end > meeting_end_limit:
            break
        if is_friday and start > FRIDAY_LATEST_START:
            continue

        overlaps = any(start < busy_end and end > busy_start for busy_start, busy_end in busy_intervals)
        if not overlaps:
            slots.append(_to_hhmm(start))

    return slots
