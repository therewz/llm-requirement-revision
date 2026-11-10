from typing import List, Dict, Tuple


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
            for the requested day.
        meeting_duration: Desired meeting length in minutes.
        day: Identifies the requested day; working hours are the same each day.

    Returns:
        All valid start times at one-minute resolution within 09:00-17:00,
        formatted as "HH:MM" and sorted ascending. Nonpositive durations
        return an empty list. Meetings may touch, but not overlap, events.
    """
    if meeting_duration <= 0:
        return []

    def hhmm_to_minutes(t: str) -> int:
        h, m = t.split(":")
        return int(h) * 60 + int(m)

    def minutes_to_hhmm(x: int) -> str:
        return f"{x // 60:02d}:{x % 60:02d}"

    WORK_START = hhmm_to_minutes("09:00")
    WORK_END = hhmm_to_minutes("17:00")

    busy: List[Tuple[int, int]] = []

    for event in events:
        start = hhmm_to_minutes(event["start"])
        end = hhmm_to_minutes(event["end"])
        if end <= start:
            continue

        # Ignore events fully outside working hours.
        if end <= WORK_START or start >= WORK_END:
            continue

        busy.append((max(start, WORK_START), min(end, WORK_END)))

    busy.sort(key=lambda interval: interval[0])

    merged: List[Tuple[int, int]] = []
    for start, end in busy:
        if merged and start < merged[-1][1]:
            last_start, last_end = merged[-1]
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    def conflicts(start: int, end: int) -> bool:
        return any(start < busy_end and end > busy_start
                   for busy_start, busy_end in merged)

    return [
        minutes_to_hhmm(start)
        for start in range(WORK_START, WORK_END - meeting_duration + 1)
        if not conflicts(start, start + meeting_duration)
    ]
