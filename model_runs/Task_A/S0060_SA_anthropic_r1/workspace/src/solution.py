from typing import List, Optional
import datetime
import re

WORK_START = 8 * 60         # 08:00
WORK_END = 17 * 60          # 17:00
LAST_START_LIMIT = 11 * 60  # no suggested start time at 11:00 or later
STEP = 15                   # candidate start times every 15 minutes


def time_to_minutes(t: str) -> int:
    if not isinstance(t, str):
        raise ValueError("Time must be a string")
    t = t.strip()
    if not re.fullmatch(r"\d{1,2}:\d{2}", t):
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
    except (ValueError, TypeError):
        raise ValueError("Invalid date")


def _parse_event(ev: str):
    """Parse an event string of the form 'HH:MM-HH:MM' (24-hour clock)."""
    if not isinstance(ev, str):
        raise ValueError("Events must be strings")
    parts = ev.split("-")
    if len(parts) != 2:
        raise ValueError("Event must be of the form 'HH:MM-HH:MM'")
    s = time_to_minutes(parts[0])
    e = time_to_minutes(parts[1])
    if s >= e:
        raise ValueError("Invalid event interval")
    return s, e


def suggest_slots(events: List[str], meeting_duration: int, day: Optional[str] = None) -> List[str]:
    # -------- VALIDATION --------
    if not isinstance(events, list):
        raise ValueError("Events must be a list")
    if not all(isinstance(e, str) for e in events):
        raise ValueError("Events must only contain strings")
    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int):
        raise ValueError("Meeting duration must be int")
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")
    if day is not None:
        validate_date(day)

    duration = meeting_duration * 60  # duration is given in hours

    # -------- PROCESS EVENTS --------
    busy = []
    for ev in events:
        s, e = _parse_event(ev)
        s = max(s, WORK_START)
        e = min(e, WORK_END)
        if s < e:
            busy.append((s, e))

    # -------- FIND SLOTS (earliest first) --------
    slots = []
    current = WORK_START
    while current < LAST_START_LIMIT and current + duration <= WORK_END:
        end = current + duration
        if not any(current < e and end > s for s, e in busy):
            slots.append(minutes_to_time(current))
        current += STEP

    return slots
