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
    """Return available HH:MM starts in chronological order.

    Events contain string-valued ``start`` and ``end`` times. The meeting
    duration is a positive integer number of hours. Starts are considered at
    each minute from 08:00 up to, but not including, 11:00, and the entire
    meeting must fit before or at 17:00. Intervals may touch without conflicting.
    The caller supplies events for ``day``; all days use the same rules.
    """
    # -------- VALIDATION --------
    if not isinstance(events, list):
        raise ValueError("Events must be a list")
    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int):
        raise ValueError("Meeting duration must be int")
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")
    duration_minutes = meeting_duration * 60

    # -------- CONSTANTS --------
    WORK_START = 8 * 60        # 08:00
    WORK_END = 17 * 60         # 17:00
    START_CUTOFF = 11 * 60     # Starts must be earlier than 11:00

    # -------- PROCESS EVENTS --------
    busy = []
    for e in events:
        s = time_to_minutes(e["start"])
        e_ = time_to_minutes(e["end"])
        if s >= e_:
            raise ValueError("Invalid event interval")
        # Ignore events outside working hours and clip those crossing a boundary.
        s = max(s, WORK_START)
        e_ = min(e_, WORK_END)
        if s < e_:
            busy.append((s, e_))

    # Merge overlapping events
    busy.sort()
    merged = []
    for s, e_ in busy:
        if not merged or s > merged[-1][1]:
            merged.append([s, e_])
        else:
            merged[-1][1] = max(merged[-1][1], e_)

    # -------- FIND SLOTS --------
    slots = []
    current = WORK_START
    while current < START_CUTOFF and current + duration_minutes <= WORK_END:
        meeting_end = current + duration_minutes
        if not any(current < e_ and meeting_end > s for s, e_ in merged):
            slots.append(minutes_to_time(current))
        current += 1

    return slots
