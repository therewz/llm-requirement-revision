from typing import List, Dict, Optional

def convert_time_to_mins(time_str: str) -> int:
    """Convert 'HH:MM' string to minutes since 00:00 (False if invalid)."""
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            return False
        return hour * 60 + minute
    except Exception:
        return False

def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: Optional[str] = None) -> List[str]:
    """
    Suggest possible meeting start times for a given day.
    - Working hours: 09:00-17:00 (540-1020 minutes); the meeting must end by 17:00
    - Slots every 15 minutes
    - Slots overlapping existing events are excluded
    The optional `day` argument is accepted for compatibility and is not used.
    """
    WORK_START = 9 * 60  # 540 minutes
    WORK_END = 17 * 60   # 1020 minutes

    if meeting_duration <= 0:
        return []

    # Convert events to minutes for easier checking
    busy_times = []
    for event in events:
        start = convert_time_to_mins(event['start'])
        end = convert_time_to_mins(event['end'])
        if start is not False and end is not False:
            busy_times.append((start, end))

    busy_times.sort()  # sort by start time

    slots = []
    current_time = WORK_START
    while current_time + meeting_duration <= WORK_END:
        conflict = False
        for start, end in busy_times:
            if not (current_time + meeting_duration <= start or current_time >= end):
                conflict = True
                break

        if not conflict:
            slots.append(f"{current_time // 60:02d}:{current_time % 60:02d}")

        current_time += 15  # move to next 15-minute slot

    return slots
