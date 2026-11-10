from typing import List, Dict

# Define working hours and lunch
WORK_START = "09:00"
WORK_END = "17:00"
LUNCH_START = "12:00"
LUNCH_END = "13:00"
SLOT_INTERVAL = 15  # minutes between candidate start times
VALID_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def time_to_minutes(t: str) -> int:
    try:
        hours, minutes = map(int, t.split(":"))
        if not (0 <= hours < 24) or not (0 <= minutes < 60):
            raise ValueError
        return hours * 60 + minutes
    except Exception:
        raise ValueError(f"Invalid time format: {t}")


def minutes_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def prepare_events(events: List[Dict[str, str]]) -> List[tuple]:
    event_list = []
    for e in events:
        start = time_to_minutes(e['start'])
        end = time_to_minutes(e['end'])
        if start > end:
            raise ValueError(f"Event start {e['start']} must not be after end {e['end']}")
        if start == end:
            continue  # zero-length event blocks nothing
        event_list.append((start, end))
    return sorted(event_list)


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # Non-positive duration: nothing can be scheduled
    if meeting_duration <= 0:
        return []

    if day not in VALID_DAYS:
        raise ValueError(f"Invalid day: {day}")

    work_start = time_to_minutes(WORK_START)
    work_end = time_to_minutes(WORK_END)

    # Lunch is a blocked interval
    blocked = prepare_events(list(events) + [{"start": LUNCH_START, "end": LUNCH_END}])

    valid_slots = []
    slot_start = ((work_start + SLOT_INTERVAL - 1) // SLOT_INTERVAL) * SLOT_INTERVAL
    while slot_start + meeting_duration <= work_end:
        slot_end = slot_start + meeting_duration
        # Overlap if slot starts before event ends and ends after event starts
        if not any(slot_start < end and slot_end > start for start, end in blocked):
            valid_slots.append(minutes_to_time(slot_start))
        slot_start += SLOT_INTERVAL

    return valid_slots
