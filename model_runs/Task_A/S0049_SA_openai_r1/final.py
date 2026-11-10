"""Suggest meeting start times within fixed working hours and around busy periods."""
from typing import List, Dict

WORK_START = 9 * 60
WORK_END = 15 * 60
LUNCH_START = 12 * 60
LUNCH_END = 13 * 60
SLOT_STEP = 15


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


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Return all feasible meeting starts on a 15-minute grid, earliest first.

    Work hours are 09:00-15:00, lunch (12:00-13:00) is unavailable,
    and each valid calendar event has a 15-minute cooldown afterward.
    Events are clipped to work hours; invalid or wholly outside events
    are ignored. The day value is accepted but not used.

    meeting_duration must be a positive integer number of minutes.
    Invalid durations and schedules with no suitable slots return [].
    """
    if (
        not isinstance(meeting_duration, int)
        or isinstance(meeting_duration, bool)
        or meeting_duration <= 0
        or meeting_duration > WORK_END - WORK_START
    ):
        return []

    busy_intervals: List[tuple[int, int]] = []
    for event in events:
        start = _to_minutes(event["start"])
        end = _to_minutes(event["end"])
        if end <= start or end <= WORK_START or start >= WORK_END:
            continue

        clipped_start = max(start, WORK_START)
        clipped_end = min(end + SLOT_STEP, WORK_END)
        busy_intervals.append((clipped_start, clipped_end))

    busy_intervals.append((LUNCH_START, LUNCH_END))
    busy_intervals = _merge_intervals(busy_intervals)

    slots: List[str] = []
    for start in range(WORK_START, WORK_END - meeting_duration + 1, SLOT_STEP):
        end = start + meeting_duration
        overlaps = any(
            start < busy_end and end > busy_start
            for busy_start, busy_end in busy_intervals
        )
        if not overlaps:
            slots.append(_to_hhmm(start))

    return slots
