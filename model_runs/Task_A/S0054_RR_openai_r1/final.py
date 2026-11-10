from typing import List, Dict
from datetime import datetime

WORK_START = "09:00"
WORK_END = "17:00"
FRIDAY_END = "15:00"  # latest meeting start on Friday


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
    """Return all feasible minute-by-minute starts in chronological order.

    Meetings must fit entirely within working hours. Events block [start, end),
    so a meeting may start when an event ends or end when an event starts.
    On Fridays, meetings may start at 15:00 but not later.
    """
    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be a positive integer")

    try:
        dt = datetime.strptime(day, "%Y-%m-%d")
    except Exception:
        raise ValueError(f"Invalid date: {day}")

    work_start = time_to_minutes(WORK_START)
    work_end = time_to_minutes(WORK_END)
    if meeting_duration > work_end - work_start:
        return []

    latest_start = work_end - meeting_duration
    if dt.weekday() == 4:
        latest_start = min(latest_start, time_to_minutes(FRIDAY_END))

    # Clip to working hours, then merge overlapping or back-to-back events.
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

    # The sentinel includes the free interval after the final event.
    slots = []
    prev_end = work_start
    for start, end in merged + [[work_end, work_end]]:
        last_start = min(start - meeting_duration, latest_start)
        slots.extend(minutes_to_time(t) for t in range(prev_end, last_start + 1))
        prev_end = end

    return slots
