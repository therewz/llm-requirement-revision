from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # Validate meeting duration (minutes)
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    # Business hours (HH:MM, 24 hour)
    BUSINESS_START = "09:00"
    BUSINESS_END = "17:00"
    SLOT_INCREMENT = 15

    def time_to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
        except Exception:
            raise ValueError(f"Invalid time format: {t}")
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError(f"Invalid time value: {t}")
        return h * 60 + m

    def minutes_to_time(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    day_start = time_to_minutes(BUSINESS_START)
    day_end = time_to_minutes(BUSINESS_END)

    # Validate and normalize events
    intervals = []
    for e in events:
        try:
            start = time_to_minutes(e['start'])
            end = time_to_minutes(e['end'])
        except KeyError:
            raise ValueError("Event must have 'start' and 'end'")
        if start >= end:
            raise ValueError(f"Event start >= end: {e}")
        intervals.append((start, end))
    intervals.sort()

    # Find free gaps within business hours (a meeting may start right when an event ends)
    free_slots = []
    cursor = day_start
    for start, end in intervals:
        if end <= cursor:
            continue
        if start > cursor:
            free_slots.append((cursor, min(start, day_end)))
        cursor = max(cursor, end)
        if cursor >= day_end:
            break
    if cursor < day_end:
        free_slots.append((cursor, day_end))

    # Generate candidate start times within each gap
    available_starts = []
    for gap_start, gap_end in free_slots:
        slot_start = gap_start
        while slot_start + meeting_duration <= gap_end:
            available_starts.append(minutes_to_time(slot_start))
            slot_start += SLOT_INCREMENT

    return available_starts
