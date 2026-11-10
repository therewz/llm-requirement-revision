from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return all feasible minute-resolution starts within 09:00–17:00.

    The day is informational only. Meetings may start when an event ends or
    end when an event starts; only overlapping time is excluded.
    """
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    work_start = 9 * 60
    work_end = 17 * 60

    # Convert events and retain only their portions within working hours.
    busy_intervals = []
    for event in events:
        try:
            start_h, start_m = map(int, event['start'].split(':'))
            end_h, end_m = map(int, event['end'].split(':'))
        except (KeyError, AttributeError, TypeError, ValueError):
            raise ValueError("Invalid time format in events")
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        if start >= end:
            raise ValueError("Event start time must be before end time")
        start = max(start, work_start)
        end = min(end, work_end)
        if start < end:
            busy_intervals.append((start, end))

    # Sorting and merging handles unsorted, overlapping, and adjacent events.
    busy_intervals.sort()
    merged = []
    for start, end in busy_intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    free_intervals = []
    prev_end = work_start
    for start, end in merged:
        if start - prev_end >= meeting_duration:
            free_intervals.append((prev_end, start))
        prev_end = end
    if work_end - prev_end >= meeting_duration:
        free_intervals.append((prev_end, work_end))

    slots = []
    for start, end in free_intervals:
        for minute in range(start, end - meeting_duration + 1):
            slots.append(f"{minute // 60:02d}:{minute % 60:02d}")
    return slots
