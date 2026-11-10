from typing import List, Dict
import datetime
import re


def time_to_minutes(t: str) -> int:
    if not re.match(r"^\d{2}:\d{2}$", t):
        raise ValueError("Invalid time format")
    h, m = map(int, t.split(":"))
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("Invalid time value")
    return h * 60 + m


def minutes_to_time(m: int) -> str:
    return f"{m//60:02d}:{m%60:02d}"


def validate_date(day: str):
    try:
        return datetime.datetime.strptime(day, "%Y-%m-%d")
    except:
        raise ValueError("Invalid date")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return available HH:MM starts, in chronological order.

    meeting_duration is a positive integer number of hours. Events may use
    the existing {"start": "HH:MM", "end": "HH:MM"} representation or be
    strings of the form "HH:MM-HH:MM". Intervals are half-open, so meetings
    can start exactly when an event ends or end exactly when one starts.

    Meetings must fit within 08:00-17:00 and start before 11:00. The Friday
    cutoff of 15:00 also applies, though the before-11:00 rule is stricter.
    """
    if not isinstance(events, list):
        raise ValueError("Events must be a list")
    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int):
        raise ValueError("Meeting duration must be int")
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    date_obj = validate_date(day)
    is_friday = date_obj.weekday() == 4
    duration_minutes = meeting_duration * 60

    WORK_START = 8 * 60
    WORK_END = 17 * 60
    START_CUTOFF = 11 * 60  # Starts at 11:00 or later are not allowed.
    FRIDAY_LAST_START = 15 * 60

    busy = []
    for event in events:
        if isinstance(event, str):
            times = event.split("-")
            if len(times) != 2:
                raise ValueError("Event must have start and end times")
            start_time, end_time = times
        else:
            start_time, end_time = event["start"], event["end"]
        start = time_to_minutes(start_time)
        end = time_to_minutes(end_time)
        if start >= end:
            raise ValueError("Invalid event interval")

        start = max(start, WORK_START)
        end = min(end, WORK_END)
        if start < end:
            busy.append((start, end))

    busy.sort()
    merged = []
    for start, end in busy:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    slots = []
    last_start = min(WORK_END - duration_minutes, START_CUTOFF - 1)
    for current in range(WORK_START, last_start + 1):
        if is_friday and current > FRIDAY_LAST_START:
            continue
        meeting_end = current + duration_minutes
        if not any(current < end and meeting_end > start for start, end in merged):
            slots.append(minutes_to_time(current))

    return slots
