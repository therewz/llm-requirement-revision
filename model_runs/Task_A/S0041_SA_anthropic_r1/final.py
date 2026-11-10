from typing import List, Dict, Optional

SLOT_STEP = 30

# ----------------------------
# Helpers
# ----------------------------

def to_minutes(t: str) -> int:
    try:
        h, m = map(int, t.split(":"))
        if not (0 <= h < 24) or not (0 <= m < 60):
            raise ValueError
        return h * 60 + m
    except Exception:
        raise ValueError(f"Invalid time format: {t}")

def to_time_str(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"

def merge_intervals(intervals: List[List[int]]) -> List[List[int]]:
    if not intervals:
        return []
    intervals.sort()
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        last_end = merged[-1][1]
        if start <= last_end:
            merged[-1][1] = max(last_end, end)
        else:
            merged.append([start, end])
    return merged

# ----------------------------
# Main function
# ----------------------------

def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: Optional[str] = None) -> List[str]:
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive.")

    WORK_START = to_minutes("09:00")
    WORK_END = to_minutes("17:00")

    intervals = []
    for e in events or []:
        start = to_minutes(e["start"])
        end = to_minutes(e["end"])
        if start >= end:
            raise ValueError(f"Event start time {e['start']} >= end time {e['end']}")
        start = max(start, WORK_START)
        end = min(end, WORK_END)
        if start < end:
            intervals.append([start, end])

    # Lunch break
    intervals.append([to_minutes("12:00"), to_minutes("13:00")])

    blocked = merge_intervals(intervals)

    # Slots every 30 minutes, in ascending order
    valid_slots = []
    current = WORK_START
    while current + meeting_duration <= WORK_END:
        meeting_end = current + meeting_duration
        conflict = any(not (meeting_end <= start or current >= end) for start, end in blocked)
        if not conflict:
            valid_slots.append(to_time_str(current))
        current += SLOT_STEP

    return valid_slots
