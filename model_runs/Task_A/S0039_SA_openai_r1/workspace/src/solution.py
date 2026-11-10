from typing import List, Dict

# Define working hours and lunch.
WORK_START = "09:00"
WORK_END = "17:00"
LUNCH_START = "12:00"
LUNCH_END = "13:00"
SLOT_INTERVAL = 1  # Time inputs have minute precision; include every valid start.


def time_to_minutes(t: str) -> int:
    try:
        hours, minutes = map(int, t.split(":"))
        if not (0 <= hours < 24) or not (0 <= minutes < 60):
            raise ValueError
        return hours * 60 + minutes
    except Exception:
        raise ValueError(f"Invalid time format: {t}")


def minutes_to_time(m: int) -> str:
    hours = m // 60
    minutes = m % 60
    return f"{hours:02d}:{minutes:02d}"


def prepare_events(events: List[Dict[str, str]]) -> List[tuple]:
    event_list = []
    for e in events:
        start = time_to_minutes(e['start'])
        end = time_to_minutes(e['end'])
        if start > end:
            raise ValueError(f"Event start {e['start']} must not be after end {e['end']}")
        # A zero-duration event occupies no time.
        if start < end:
            event_list.append((start, end))
    return sorted(event_list)


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    if meeting_duration <= 0:
        return []

    if day not in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
        raise ValueError(f"Invalid day: {day}")

    work_start = time_to_minutes(WORK_START)
    work_end = time_to_minutes(WORK_END)

    # Lunch blocks time just like an existing event. Do not mutate the input.
    event_times = prepare_events(events + [{"start": LUNCH_START, "end": LUNCH_END}])

    # Merge overlapping and back-to-back events.
    merged_events = []
    for start, end in event_times:
        if merged_events and start <= merged_events[-1][1]:
            merged_events[-1][1] = max(merged_events[-1][1], end)
        else:
            merged_events.append([start, end])

    # Find free intervals, ignoring portions of events outside working hours.
    free_slots = []
    current = work_start
    for start, end in merged_events:
        start = max(start, work_start)
        end = min(end, work_end)
        if start >= end:
            continue
        if start - current >= meeting_duration:
            free_slots.append((current, start))
        current = max(current, end)
    if work_end - current >= meeting_duration:
        free_slots.append((current, work_end))

    valid_slots = []
    for start, end in free_slots:
        for slot_start in range(start, end - meeting_duration + 1, SLOT_INTERVAL):
            valid_slots.append(minutes_to_time(slot_start))

    return valid_slots
