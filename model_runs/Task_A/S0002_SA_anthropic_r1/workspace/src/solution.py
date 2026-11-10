from typing import List, Dict, Optional


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: Optional[str] = None
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
        meeting_duration: Desired meeting length in minutes
        day: Optional day label; not used, since the same rules apply every day.

    Returns:
        List of valid start times as "HH:MM" sorted ascending. Empty if none.
    """
    WORK_START = 9 * 60   # 09:00
    WORK_END = 17 * 60    # 17:00
    STEP = 15

    def time_to_minutes(time_str: str) -> int:
        hour, minute = map(int, time_str.strip().split(":"))
        return hour * 60 + minute

    def minutes_to_time(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    if meeting_duration <= 0:
        return []

    busy = [(time_to_minutes(e["start"]), time_to_minutes(e["end"])) for e in events]

    slots = []
    for start in range(WORK_START, WORK_END, STEP):
        end = start + meeting_duration
        if end > WORK_END:
            break
        # Back-to-back meetings are allowed; only true overlaps conflict.
        if any(start < b_end and end > b_start for b_start, b_end in busy):
            continue
        slots.append(minutes_to_time(start))
    return slots
