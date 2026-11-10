from typing import List, Dict

WORK_START = 9 * 60
WORK_END = 17 * 60
LUNCH_START = 12 * 60
LUNCH_END = 13 * 60
BUFFER = 15
GRANULARITY = 15


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
    if (
        not isinstance(meeting_duration, int)
        or isinstance(meeting_duration, bool)
        or meeting_duration <= 0
    ):
        raise ValueError("Meeting duration must be a positive integer number of minutes")

    if not isinstance(day, str) or day.lower() not in {
        "mo", "tu", "we", "th", "fr", "sa", "su"
    }:
        raise ValueError(f"Invalid day abbreviation: {day}")

    if not isinstance(events, list):
        raise ValueError("Events must be a list of dictionaries")

    blocked = []
    for e in events:
        if not isinstance(e, dict) or "end" not in e or not (
            "start" in e or "begin" in e
        ):
            raise ValueError("Each event must contain start (or begin) and end times")
        start = to_minutes(e["start"] if "start" in e else e["begin"])
        end = to_minutes(e["end"])
        if start >= end:
            raise ValueError(f"Event start must be before end: {e}")
        # Leave a break between the proposed meeting and either neighboring event.
        blocked.append((start - BUFFER, end + BUFFER))

    # Lunch is already a break, so it does not need an additional buffer.
    blocked.append((LUNCH_START, LUNCH_END))
    blocked = merge_intervals(blocked)

    slots = []
    current = WORK_START
    for start, end in blocked:
        gap_end = min(start, WORK_END)
        t = current
        while t + meeting_duration <= gap_end:
            slots.append(to_time_str(t))
            t += GRANULARITY
        current = max(current, end)

    t = current
    while t + meeting_duration <= WORK_END:
        slots.append(to_time_str(t))
        t += GRANULARITY

    return sorted(slots)
