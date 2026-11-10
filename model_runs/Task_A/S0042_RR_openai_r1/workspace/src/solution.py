from typing import List, Dict

WORK_START = 9 * 60
WORK_END = 17 * 60
LUNCH_START = 12 * 60
LUNCH_END = 13 * 60
BUFFER = 15
GRANULARITY = 1  # HH:MM inputs allow starts at any whole minute.
FRIDAY_CUTOFF = 15 * 60  # Latest Friday start, inclusive.


def to_minutes(t: str) -> int:
    if (
        not isinstance(t, str)
        or len(t) != 5
        or t[2] != ":"
        or any(c not in "0123456789" for c in t[:2] + t[3:])
    ):
        raise ValueError(f"Invalid time format: {t}")
    h, m = int(t[:2]), int(t[3:])
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"Invalid time format: {t}")
    return h * 60 + m


def to_time_str(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def merge_intervals(intervals):
    intervals.sort()
    merged = []

    for start, end in intervals:
        if not merged or merged[-1][1] < start:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    return merged


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return minute-resolution starts, with a 15-minute gap from other meetings.

    Days use two-letter abbreviations (Mo, Tu, We, Th, Fr, Sa, Su),
    case-insensitively. Events use start/end, with begin also accepted for start.
    Lunch is unavailable but is not itself a meeting requiring an extra buffer.
    """
    if (
        not isinstance(meeting_duration, int)
        or isinstance(meeting_duration, bool)
        or meeting_duration <= 0
    ):
        raise ValueError("Meeting duration must be a positive integer number of minutes")

    if not isinstance(day, str) or day.lower() not in {
        "mo", "tu", "we", "th", "fr", "sa", "su"
    }:
        raise ValueError("Day must be a two-letter abbreviation: Mo, Tu, We, Th, Fr, Sa, Su")

    if not isinstance(events, list):
        raise ValueError("Events must be a list of dictionaries")

    blocked = []
    for event in events:
        if not isinstance(event, dict) or "end" not in event:
            raise ValueError("Each event must contain start (or begin) and end times")
        if "start" in event:
            start_value = event["start"]
        elif "begin" in event:
            start_value = event["begin"]
        else:
            raise ValueError("Each event must contain start (or begin) and end times")
        start = to_minutes(start_value)
        end = to_minutes(event["end"])
        if start >= end:
            raise ValueError(f"Event start must be before end: {event}")
        # A new meeting must leave a break both before and after existing ones.
        blocked.append((start - BUFFER, end + BUFFER))

    blocked.append((LUNCH_START, LUNCH_END))
    blocked = merge_intervals(blocked)

    latest_start = WORK_END - meeting_duration
    if day.lower() == "fr":
        latest_start = min(latest_start, FRIDAY_CUTOFF)

    slots = []
    current = WORK_START
    for start, end in blocked:
        gap_last_start = min(start - meeting_duration, latest_start)
        while current <= gap_last_start:
            slots.append(to_time_str(current))
            current += GRANULARITY
        current = max(current, end)

    while current <= latest_start:
        slots.append(to_time_str(current))
        current += GRANULARITY

    return slots
