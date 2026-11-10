from typing import List, Dict
from datetime import datetime

WORK_START = "09:00"
WORK_END = "17:00"
SLOT_GRANULARITY = 15  # minutes
FRIDAY_LATEST_START = "15:00"  # latest meeting start on Friday (inclusive)

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
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    try:
        dt = datetime.strptime(day, "%Y-%m-%d")
    except Exception:
        raise ValueError(f"Invalid date: {day}")

    work_start = time_to_minutes(WORK_START)
    work_end = time_to_minutes(WORK_END)

    # Latest allowed start time
    latest_start = work_end - meeting_duration
    if dt.weekday() == 4:  # Friday: no meeting may start after 15:00
        latest_start = min(latest_start, time_to_minutes(FRIDAY_LATEST_START))

    # Validate events (always, even if no slot can exist)
    busy = []
    for e in events:
        validate_event(e)
        busy.append((time_to_minutes(e["start"]), time_to_minutes(e["end"])))

    if meeting_duration > work_end - work_start:
        return []

    slots = []
    start = work_start
    while start <= latest_start:
        end = start + meeting_duration
        # Back-to-back is allowed: overlap only if intervals strictly intersect
        if all(end <= b_start or start >= b_end for b_start, b_end in busy):
            slots.append(minutes_to_time(start))
        start += SLOT_GRANULARITY

    return slots
