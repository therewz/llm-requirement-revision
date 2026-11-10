from typing import List, Dict, Optional


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: Optional[str] = None
) -> List[str]:
    """
    Suggest possible meeting start times for a day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
        meeting_duration: Desired meeting length in minutes
        day: Optional date string; accepted for compatibility, not used.

    Returns:
        List of valid start times as "HH:MM" sorted ascending
        (empty if none are available).
    """
    WORK_START = 9 * 60   # 9:00
    WORK_END = 17 * 60    # 17:00
    STEP = 15

    if meeting_duration <= 0:
        return []

    def to_minutes(t: str) -> int:
        h, m = map(int, t.strip().split(":"))
        return h * 60 + m

    def to_time_str(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    busy_intervals = []
    for event in events:
        start = to_minutes(event["start"])
        end = to_minutes(event["end"])
        if start < end:
            busy_intervals.append((start, end))
    busy_intervals.sort()

    available_starts = []
    for start in range(WORK_START, WORK_END - meeting_duration + 1, STEP):
        end = start + meeting_duration
        if all(end <= bs or start >= be for bs, be in busy_intervals):
            available_starts.append(to_time_str(start))

    return available_starts
