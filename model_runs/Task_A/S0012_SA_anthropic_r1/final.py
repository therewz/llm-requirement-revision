from typing import List, Dict, Optional
from datetime import datetime, timedelta


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: Optional[str] = None
) -> List[str]:
    """Return valid "HH:MM" start times (15-minute increments) within working
    hours (09:00-17:00) where a meeting of meeting_duration minutes does not
    overlap any existing event. Back-to-back meetings are allowed."""

    if meeting_duration <= 0:
        return []

    fmt = "%H:%M"
    WORK_START = datetime.strptime("09:00", fmt)
    WORK_END = datetime.strptime("17:00", fmt)

    parsed_events = []
    for e in events:
        start = datetime.strptime(e["start"], fmt)
        end = datetime.strptime(e["end"], fmt)
        if end <= start:
            continue
        parsed_events.append((start, end))

    slots = []
    current = WORK_START
    delta = timedelta(minutes=15)
    meeting_delta = timedelta(minutes=meeting_duration)

    while current + meeting_delta <= WORK_END:
        meeting_end = current + meeting_delta

        # Overlap if the intervals intersect (touching endpoints is fine)
        overlap = any(
            current < event_end and meeting_end > event_start
            for event_start, event_end in parsed_events
        )

        if not overlap:
            slots.append(current.strftime(fmt))

        current += delta

    return slots
