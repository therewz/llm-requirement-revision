from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return the earliest non-overlapping meeting starts between 09:00 and 17:00.

    Durations are in minutes. Three-letter day names are case-insensitive;
    Saturdays and Sundays have no working hours.
    """
    if not isinstance(day, str) or len(day) != 3 or not day.isalpha():
        raise ValueError("Day must be a three-letter string")

    if not isinstance(meeting_duration, int) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be an integer greater than 0")

    def to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
            return h * 60 + m
        except (AttributeError, TypeError, ValueError):
            raise ValueError("Invalid time format") from None

    def to_str(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    WORK_START = 9 * 60
    WORK_END = 17 * 60

    # Normalize events, ignoring portions outside working hours.
    intervals = []
    for event in events:
        start = to_minutes(event["start"])
        end = to_minutes(event["end"])
        if start >= end:
            raise ValueError("Invalid event interval")

        start = max(start, WORK_START)
        end = min(end, WORK_END)
        if start < end:
            intervals.append((start, end))

    if day.lower() in ("sat", "sun"):
        return []

    # Merge busy intervals so overlapping or duplicate events are handled once.
    intervals.sort()
    merged = []
    for start, end in intervals:
        if not merged or merged[-1][1] < start:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    free = []
    previous_end = WORK_START
    for start, end in merged:
        if previous_end < start:
            free.append((previous_end, start))
        previous_end = max(previous_end, end)
    if previous_end < WORK_END:
        free.append((previous_end, WORK_END))

    # Prefer the earliest start in each gap, then advance by the full duration
    # so suggested meetings do not overlap one another.
    result = []
    for start, end in free:
        current = start
        while current + meeting_duration <= end:
            result.append(to_str(current))
            current += meeting_duration

    return result
