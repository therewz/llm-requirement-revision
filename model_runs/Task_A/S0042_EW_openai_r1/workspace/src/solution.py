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
    # Validate inputs against the expected types and formats.
    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int):
        raise ValueError("Meeting duration must be an integer number of minutes")
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")
    if not isinstance(day, str) or day.lower() not in {
        "mo", "tu", "we", "th", "fr", "sa", "su"
    }:
        raise ValueError(f"Invalid day abbreviation: {day}")
    if not isinstance(events, list):
        raise ValueError("Events must be a list of dictionaries")

    # Step 1: convert events and reserve a break on either side so a
    # suggested meeting has at least 15 minutes between it and any event.
    blocked = []

    for e in events:
        if not isinstance(e, dict) or "start" not in e or "end" not in e:
            raise ValueError("Each event must have start and end time strings")
        start = to_minutes(e["start"])
        end = to_minutes(e["end"])
        if start >= end:
            raise ValueError(f"Event start must be before end: {e}")
        blocked.append((start - BUFFER, end + BUFFER))

    # Step 2: add lunch break
    blocked.append((LUNCH_START, LUNCH_END))

    # Step 3: merge overlaps
    blocked = merge_intervals(blocked)

    # Step 4: find available gaps, using the same working hours every day.
    slots = []
    current = WORK_START

    for start, end in blocked:
        if current < start:
            gap_start = current
            gap_end = min(start, WORK_END)

            # Generate slots every 15 minutes.
            t = gap_start
            while t + meeting_duration <= gap_end:
                if t >= WORK_START:
                    slots.append(to_time_str(t))
                t += GRANULARITY

        current = max(current, end)

    # Last gap after final event
    if current < WORK_END:
        t = current
        while t + meeting_duration <= WORK_END:
            slots.append(to_time_str(t))
            t += GRANULARITY

    return sorted(slots)
