"""
Meeting slot suggestion.

Working hours are 09:00-17:00, lunch 12:00-13:00 is blocked, and slots are
generated in 15-minute increments without overlapping existing events.
"""

from typing import List, Dict


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
        meeting_duration: Desired meeting length in minutes
        day: Three-letter day abbreviation (e.g., "Mon", "Tue", ... "Fri")

    Returns:
        List of valid start times as "HH:MM" sorted ascending
    """

    def to_minutes(t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m

    def to_time(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    WORK_START = to_minutes("09:00")
    WORK_END = to_minutes("17:00")
    LUNCH_START = to_minutes("12:00")
    LUNCH_END = to_minutes("13:00")

    # Convert events, ignoring those entirely outside working hours
    busy = []
    for e in events:
        start = to_minutes(e["start"])
        end = to_minutes(e["end"])
        if end <= WORK_START or start >= WORK_END:
            continue
        busy.append((start, end))

    # Lunch break is always blocked
    busy.append((LUNCH_START, LUNCH_END))
    busy.sort()

    slots = []
    t = WORK_START
    while t + meeting_duration <= WORK_END:
        meeting_end = t + meeting_duration
        # Overlap only if intervals intersect; touching endpoints are fine
        if all(not (t < bend and meeting_end > bstart) for bstart, bend in busy):
            slots.append(to_time(t))
        t += 15

    return slots
