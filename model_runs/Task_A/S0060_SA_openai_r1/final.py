from typing import List, Dict
import datetime
import re


def time_to_minutes(t: str) -> int:
    if not isinstance(t, str) or not re.fullmatch(r"[0-9]{1,2}:[0-9]{2}", t):
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
    except (TypeError, ValueError):
        raise ValueError("Invalid date")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return all available minute-precision starts, in chronological order.

    ``meeting_duration`` is a positive integer number of hours. Meetings must
    fit within 08:00-17:00 and start before 11:00.

    Events can be start/end dictionaries, strings such as "09:00-10:30", or
    individual "HH:MM" strings denoting one-hour events. Event intervals are
    half-open, so a meeting can start exactly when an event ends.

    ``day`` is retained for compatibility; the events already describe that
    day, and availability does not depend on its date or weekday.
    """
    if not isinstance(events, list):
        raise ValueError("Events must be a list")
    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int):
        raise ValueError("Meeting duration must be int")
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    work_start = 8 * 60
    work_end = 17 * 60
    last_start_exclusive = 11 * 60
    duration_minutes = meeting_duration * 60

    busy = []
    for event in events:
        if isinstance(event, str):
            if "-" in event:
                parts = event.split("-")
                if len(parts) != 2:
                    raise ValueError("Invalid event interval")
                start = time_to_minutes(parts[0])
                end = time_to_minutes(parts[1])
            else:
                start = time_to_minutes(event)
                end = start + 60
        elif isinstance(event, dict):
            start = time_to_minutes(event["start"])
            end = time_to_minutes(event["end"])
        else:
            raise ValueError("Events must contain time strings or start/end dictionaries")

        if start >= end:
            raise ValueError("Invalid event interval")
        start = max(start, work_start)
        end = min(end, work_end)
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
    for current in range(work_start, min(last_start_exclusive, work_end - duration_minutes + 1)):
        meeting_end = current + duration_minutes
        if all(meeting_end <= start or current >= end for start, end in merged):
            slots.append(minutes_to_time(current))
    return slots
