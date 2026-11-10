from typing import List, Dict, Optional

WORK_START = "09:00"
WORK_END = "17:00"
SLOT_GRANULARITY = 15  # minutes between candidate start times


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


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int,
                  day: Optional[str] = None) -> List[str]:
    """Return sorted HH:MM start times for a meeting of meeting_duration minutes
    that lie within working hours and do not overlap any event.
    Events are single-day dicts with "start"/"end" HH:MM; back-to-back is allowed.
    The day argument is accepted for compatibility and does not affect the result."""
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    work_start = time_to_minutes(WORK_START)
    work_end = time_to_minutes(WORK_END)

    busy = []
    for e in events or []:
        validate_event(e)
        busy.append((time_to_minutes(e["start"]), time_to_minutes(e["end"])))

    if meeting_duration > work_end - work_start:
        return []

    slots = []
    start = work_start
    while start + meeting_duration <= work_end:
        end = start + meeting_duration
        if all(end <= bs or start >= be for bs, be in busy):
            slots.append(minutes_to_time(start))
        start += SLOT_GRANULARITY
    return slots
