from typing import List, Dict


def time_to_minutes(t: str) -> int:
    try:
        hours, minutes = map(int, t.split(":"))
        if not (0 <= hours < 24 and 0 <= minutes < 60):
            raise ValueError
        return hours * 60 + minutes
    except Exception:
        raise ValueError(f"Invalid time format: {t}")


def minutes_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def validate_events(events: List[Dict[str, str]]):
    for e in events:
        start = time_to_minutes(e["start"])
        end = time_to_minutes(e["end"])
        if start >= end:
            raise ValueError(f"Event start must be before end: {e}")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    validate_events(events)

    WORK_START = time_to_minutes("09:00")
    WORK_END = time_to_minutes("17:00")
    LUNCH_START = time_to_minutes("12:00")
    LUNCH_END = time_to_minutes("13:00")
    SLOT_GRANULARITY = 15

    # Convert events to minutes (order-independent) and add lunch
    blocked = [(time_to_minutes(e["start"]), time_to_minutes(e["end"])) for e in events]
    blocked.append((LUNCH_START, LUNCH_END))

    valid_slots = []
    current_time = WORK_START
    while current_time + meeting_duration <= WORK_END:
        end_time = current_time + meeting_duration
        # Back-to-back is allowed: touching endpoints are not overlaps
        if all(end_time <= b_start or current_time >= b_end for b_start, b_end in blocked):
            valid_slots.append(minutes_to_time(current_time))
        current_time += SLOT_GRANULARITY

    return valid_slots
