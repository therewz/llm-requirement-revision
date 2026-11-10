from typing import List, Dict
from datetime import datetime

# Define working hours and lunch
WORK_START = "09:00"
WORK_END = "17:00"
LUNCH_START = "12:00"
LUNCH_END = "13:00"
SLOT_INTERVAL = 15  # minutes
FRIDAY_LAST_START = "15:00"

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def time_to_minutes(t: str) -> int:
    try:
        hours, minutes = map(int, t.strip().split(":"))
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
        if start >= end:
            # Events do not cross midnight; empty/inverted events block nothing
            continue
        event_list.append((start, end))
    return sorted(event_list)


def _is_friday(day: str) -> bool:
    d = str(day).strip()
    if d[:3].lower() in DAY_NAMES:
        return d[:3].lower() == "fri"
    try:
        return datetime.strptime(d, "%Y-%m-%d").weekday() == 4
    except Exception:
        raise ValueError(f"Invalid day: {day}")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    if not isinstance(meeting_duration, int) or isinstance(meeting_duration, bool) \
            or meeting_duration <= 0:
        return []

    is_friday = _is_friday(day)

    work_start = time_to_minutes(WORK_START)
    work_end = time_to_minutes(WORK_END)
    friday_last = time_to_minutes(FRIDAY_LAST_START)

    blocked = prepare_events(
        list(events) + [{"start": LUNCH_START, "end": LUNCH_END}]
    )

    valid_slots: List[str] = []
    # First candidate aligned to the slot interval
    start = ((work_start + SLOT_INTERVAL - 1) // SLOT_INTERVAL) * SLOT_INTERVAL
    while start + meeting_duration <= work_end:
        if is_friday and start > friday_last:
            break
        end = start + meeting_duration
        if all(end <= b_start or start >= b_end for b_start, b_end in blocked):
            valid_slots.append(minutes_to_time(start))
        start += SLOT_INTERVAL

    return valid_slots
