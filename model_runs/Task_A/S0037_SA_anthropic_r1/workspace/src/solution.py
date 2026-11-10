from typing import Dict, List

"""
Meeting slot suggestion.

`suggest_slots` returns valid meeting start times for a day, respecting working
hours (09:00-17:00), lunch (12:00-13:00), a 15 minute post-meeting buffer on
user events, and 15 minute alignment of start times.
"""

TIME_INCREMENT = 15
POST_BUFFER = 15
WORK_START = 9 * 60
WORK_END = 17 * 60
LUNCH_START = 12 * 60
LUNCH_END = 13 * 60


def _to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def suggest_slots(
    events: List[Dict[str, str]], meeting_duration: int, day: str
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
        meeting_duration: Desired meeting length in minutes
        day: Day identifier (e.g. "Mon" or "YYYY-MM-DD"); the same working
            rules apply to every day.

    Returns:
        List of valid start times as "HH:MM" sorted ascending
    """
    if meeting_duration <= 0:
        return []

    # Blocked intervals [start, end). User events get a post-meeting buffer;
    # lunch does not. Overlapping intervals are effectively merged by the
    # overlap test below.
    blocked = [(LUNCH_START, LUNCH_END)]
    for event in events:
        start = _to_minutes(event["start"])
        end = _to_minutes(event["end"]) + POST_BUFFER
        blocked.append((start, end))

    output = []
    for start in range(WORK_START, WORK_END, TIME_INCREMENT):
        end = start + meeting_duration
        if end > WORK_END:
            break
        if any(start < b_end and end > b_start for b_start, b_end in blocked):
            continue
        output.append(f"{start // 60:02d}:{start % 60:02d}")

    return output
