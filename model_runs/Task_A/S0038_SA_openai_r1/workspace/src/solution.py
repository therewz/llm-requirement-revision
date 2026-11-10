"""Suggest meeting start times within working hours, avoiding events and lunch."""

from typing import List, Dict


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: str
) -> List[str]:
    """Return available start times in 15-minute increments, sorted ascending.

    Events have "start" and "end" times in HH:MM format. Meeting duration is
    a positive integer number of minutes. Working hours are 09:00-17:00 and
    lunch is 12:00-13:00, with the same hours for every day abbreviation.
    """
    def to_minutes(t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m

    def to_time(m: int) -> str:
        return f"{m//60:02d}:{m%60:02d}"

    WORK_START = to_minutes("09:00")
    WORK_END = to_minutes("17:00")
    LUNCH_START = to_minutes("12:00")
    LUNCH_END = to_minutes("13:00")

    # Convert and filter events within working hours.
    busy = []
    for e in events:
        start = to_minutes(e["start"])
        end = to_minutes(e["end"])
        if end <= WORK_START or start >= WORK_END:
            continue
        busy.append((start, end))

    # Lunch is blocked on every day.
    busy.append((LUNCH_START, LUNCH_END))
    busy.sort()

    slots = []
    t = WORK_START
    while t + meeting_duration <= WORK_END:
        meeting_end = t + meeting_duration
        valid = True
        for bstart, bend in busy:
            # Touching endpoints do not overlap.
            if t < bend and meeting_end > bstart:
                valid = False
                break
        if valid:
            slots.append(to_time(t))
        t += 15

    return slots
