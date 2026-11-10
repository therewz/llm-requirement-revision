from typing import List, Dict
from datetime import datetime


def time_to_minutes(t: str) -> int:
    """Convert 'HH:MM' string to minutes since midnight."""
    try:
        h, m = map(int, t.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except Exception:
        raise ValueError(f"Invalid time format: {t}")
    return h * 60 + m


def minutes_to_time(m: int) -> str:
    """Convert minutes since midnight to 'HH:MM' string."""
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}"


def validate_date(day: str):
    """Validate date string 'YYYY-MM-DD'."""
    try:
        dt = datetime.strptime(day, "%Y-%m-%d")
        return dt
    except ValueError:
        raise ValueError(f"Invalid date: {day}")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Print and return available starts in chronological, 15-minute increments.

    Duration may be an integer or an integer string. Events may specify an
    explicit 'end'; otherwise they last for the requested meeting duration.
    Lunch restricts start times only, as does the Friday 15:00 cutoff.
    """
    dt = validate_date(day)

    if isinstance(meeting_duration, str):
        try:
            meeting_duration = int(meeting_duration)
        except ValueError:
            raise ValueError("Meeting duration must be an integer number of minutes")
    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int):
        raise ValueError("Meeting duration must be an integer number of minutes")
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    LUNCH_START = 12 * 60
    LUNCH_END = 13 * 60
    SLOT_GRANULARITY = 15
    FRIDAY_CUTOFF = 15 * 60

    if not isinstance(events, list):
        raise ValueError("Events must be a list of dictionaries")

    normalized_events = []
    for ev in events:
        if not isinstance(ev, dict) or "start" not in ev:
            raise ValueError("Each event must be a dictionary with a start time")
        start = time_to_minutes(ev["start"])
        end = (
            time_to_minutes(ev["end"])
            if "end" in ev
            else start + meeting_duration
        )
        if start >= end:
            raise ValueError(f"Invalid event interval: {ev}")
        if start < WORK_START or end > WORK_END:
            raise ValueError(f"Event must fall within working hours: {ev}")
        normalized_events.append((start, end))

    normalized_events.sort()

    slots = []
    for current in range(WORK_START, WORK_END - meeting_duration + 1, SLOT_GRANULARITY):
        if LUNCH_START <= current < LUNCH_END:
            continue
        if dt.weekday() == 4 and current > FRIDAY_CUTOFF:
            break

        # Adjacent meetings are allowed; no extra buffer is required.
        if any(
            current < end and current + meeting_duration > start
            for start, end in normalized_events
        ):
            continue
        slots.append(minutes_to_time(current))

    print(slots)
    return slots
