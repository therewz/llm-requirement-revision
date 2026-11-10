from typing import List, Dict


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Suggest meeting start times at one-minute precision from 09:00 to 17:00.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
        meeting_duration: Desired meeting length in minutes (positive integer)
        day: Date for which events were supplied; events already belong to this day

    Returns:
        List of valid start times as "HH:MM" sorted ascending. Meetings must
        finish by 17:00 and may start or end exactly at an event boundary.
    """
    WORK_START = 9 * 60  # 09:00
    WORK_END = 17 * 60   # 17:00

    if meeting_duration <= 0:
        return []

    def to_minutes(t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m

    def to_time_str(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    # Convert events to minute intervals (clipped to working hours).
    busy_intervals = []
    for event in events:
        start = max(to_minutes(event["start"]), WORK_START)
        end = min(to_minutes(event["end"]), WORK_END)
        if start < end:
            busy_intervals.append((start, end))

    busy_intervals.sort()
    latest_start = WORK_END - meeting_duration
    available_starts = []

    for start in range(WORK_START, latest_start + 1):
        end = start + meeting_duration
        if all(end <= busy_start or start >= busy_end
               for busy_start, busy_end in busy_intervals):
            available_starts.append(to_time_str(start))

    return available_starts
