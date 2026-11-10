from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return every feasible HH:MM start within 09:00–17:00.

    Starts are considered at one-minute resolution. The day is informational,
    and a meeting may start exactly when an event ends or end when one starts.
    """
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    work_start = 9 * 60
    work_end = 17 * 60

    # Convert events and keep only their intersection with working hours.
    busy_intervals = []
    for event in events:
        try:
            start_h, start_m = map(int, event['start'].split(':'))
            end_h, end_m = map(int, event['end'].split(':'))
        except (KeyError, TypeError, AttributeError, ValueError):
            raise ValueError("Invalid time format in events")
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        if start >= end:
            raise ValueError("Event start time must be before end time")
        start = max(start, work_start)
        end = min(end, work_end)
        if start < end:
            busy_intervals.append((start, end))

    # Merge overlapping or adjacent events, regardless of input order.
    busy_intervals.sort()
    merged = []
    for start, end in busy_intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    # Enumerate all minute-aligned starts in each free interval.
    slots = []
    free_start = work_start
    for busy_start, busy_end in merged + [[work_end, work_end]]:
        for start in range(free_start, busy_start - meeting_duration + 1):
            slots.append(f"{start // 60:02d}:{start % 60:02d}")
        free_start = busy_end

    return slots
