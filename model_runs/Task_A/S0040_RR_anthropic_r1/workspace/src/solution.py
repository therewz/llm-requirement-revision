from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:

    # Translate canonical dates to the weekday names used below.
    if isinstance(day, str) and len(day) == 10:
        from datetime import date as _calendar_input_date
        try:
            _parsed_calendar_input = _calendar_input_date.fromisoformat(day)
        except ValueError:
            pass
        else:
            if _parsed_calendar_input.isoformat() == day:
                day = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[_parsed_calendar_input.weekday()]

    # Validate meeting duration (minutes)
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    # Business hours
    BUSINESS_START = "09:00"
    BUSINESS_END = "17:00"
    FRIDAY_LAST_START = "15:00"
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
    friday_last_start = time_to_minutes(FRIDAY_LAST_START)
    is_friday = isinstance(day, str) and day.strip().lower()[:3] == "fri"

    # Validate and normalize events
    busy = []
    for e in events:
        try:
            start = time_to_minutes(e['start'])
            end = time_to_minutes(e['end'])
        except KeyError:
            raise ValueError("Event must have 'start' and 'end'")
        if start >= end:
            raise ValueError(f"Event start >= end: {e}")
        busy.append((start, end))
    busy.sort()

    # Compute free gaps within business hours (a slot may start right as an event ends)
    free_slots = []
    cursor = day_start
    for start, end in busy:
        if end <= cursor:
            continue
        gap_end = min(start, day_end)
        if gap_end - cursor >= meeting_duration:
            free_slots.append((cursor, gap_end))
        cursor = max(cursor, end)
        if cursor >= day_end:
            break
    if day_end - cursor >= meeting_duration:
        free_slots.append((cursor, day_end))

    # Generate candidate start times
    available_starts = []
    for start, end in free_slots:
        if start % SLOT_INCREMENT != 0:
            start += SLOT_INCREMENT - (start % SLOT_INCREMENT)
        slot_start = start
        while slot_start + meeting_duration <= end:
            # Friday meetings must not start after 15:00
            if not (is_friday and slot_start > friday_last_start):
                available_starts.append(minutes_to_time(slot_start))
            slot_start += SLOT_INCREMENT

    return available_starts
