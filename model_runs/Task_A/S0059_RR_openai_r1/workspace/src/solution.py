from typing import List, Dict
from datetime import datetime


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return all conflict-free starts within 09:00–17:00, at minute precision.

    The day is informational except that Fridays have a 15:00 start cutoff.
    Friday may be identified by its weekday name or an ISO calendar date.
    """
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    is_friday = day.strip().casefold() in {"friday", "fri"}
    try:
        is_friday = datetime.strptime(day, "%Y-%m-%d").weekday() == 4
    except ValueError:
        # Other day labels need not be dates and do not affect scheduling.
        pass

    work_start = 9 * 60
    work_end = 17 * 60
    friday_cutoff = 15 * 60

    intervals = []
    for event in events:
        try:
            start_h, start_m = map(int, event["start"].split(":"))
            end_h, end_m = map(int, event["end"].split(":"))
        except (KeyError, ValueError, TypeError, AttributeError):
            raise ValueError("Invalid time format in events")
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        if start >= end:
            raise ValueError("Event start time must be before end time")
        # Only the portion of an event inside working hours blocks slots.
        start = max(start, work_start)
        end = min(end, work_end)
        if start < end:
            intervals.append((start, end))

    intervals.sort()
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    free_intervals = []
    prev_end = work_start
    for start, end in merged:
        if prev_end < start:
            free_intervals.append((prev_end, start))
        prev_end = end
    if prev_end < work_end:
        free_intervals.append((prev_end, work_end))

    slots = []
    for start, end in free_intervals:
        last_start = end - meeting_duration
        if is_friday:
            last_start = min(last_start, friday_cutoff)
        for minute in range(start, last_start + 1):
            slots.append(f"{minute // 60:02d}:{minute % 60:02d}")
    return slots
