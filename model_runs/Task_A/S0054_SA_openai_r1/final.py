from typing import List, Dict

WORK_START = "09:00"
WORK_END = "17:00"


def time_to_minutes(t: str) -> int:
    try:
        h, m = map(int, t.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h * 60 + m
    except Exception:
        raise ValueError(f"Invalid time format: {t}")


def minutes_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def validate_event(event: Dict[str, str]):
    if "start" not in event or "end" not in event:
        raise ValueError("Event must have start and end times")
    start = time_to_minutes(event["start"])
    end = time_to_minutes(event["end"])
    if start >= end:
        raise ValueError(f"Event start {event['start']} must be before end {event['end']}")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return every feasible minute-resolution start time, earliest first.

    Events and proposed meetings occupy half-open intervals, so meetings may
    start exactly when an event ends or end exactly when an event starts.
    The day argument is retained for compatibility; working hours are the
    same for every day.
    """
    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int):
        raise ValueError("Meeting duration must be a positive integer")
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    work_start = time_to_minutes(WORK_START)
    work_end = time_to_minutes(WORK_END)
    if meeting_duration > work_end - work_start:
        return []

    # Validate events, clip them to working hours, then merge all conflicts.
    busy_times = []
    for event in events:
        validate_event(event)
        start = max(work_start, time_to_minutes(event["start"]))
        end = min(work_end, time_to_minutes(event["end"]))
        if start < end:
            busy_times.append((start, end))

    busy_times.sort()
    merged = []
    for start, end in busy_times:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    # Enumerate every start that fits completely inside each free interval.
    slots = []
    prev_end = work_start
    for start, end in merged:
        slots.extend(
            minutes_to_time(minute)
            for minute in range(prev_end, start - meeting_duration + 1)
        )
        prev_end = end
    slots.extend(
        minutes_to_time(minute)
        for minute in range(prev_end, work_end - meeting_duration + 1)
    )
    return slots
