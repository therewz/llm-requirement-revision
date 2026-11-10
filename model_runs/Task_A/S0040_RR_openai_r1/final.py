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
    # Validate meeting duration
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    # Business hours
    BUSINESS_START = "09:00"
    BUSINESS_END = "17:00"
    FRIDAY_LAST_START = "15:00"

    # Helper to convert time string to minutes
    def time_to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
        except Exception:
            raise ValueError(f"Invalid time format: {t}")
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError(f"Invalid time value: {t}")
        return h * 60 + m

    # Helper to convert minutes to time string
    def minutes_to_time(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    # Convert business hours
    day_start = time_to_minutes(BUSINESS_START)
    day_end = time_to_minutes(BUSINESS_END)
    friday_last_start = time_to_minutes(FRIDAY_LAST_START)
    is_friday = day.lower()[:3] == "fri"

    # Validate and normalize events
    normalized_events = []
    for e in events:
        try:
            start = time_to_minutes(e['start'])
            end = time_to_minutes(e['end'])
        except KeyError:
            raise ValueError("Event must have 'start' and 'end'")
        if start >= end:
            raise ValueError(f"Event start >= end: {e}")
        normalized_events.append({'start': start, 'end': end})

    # Sort events by start time
    sorted_events = sorted(normalized_events, key=lambda x: x['start'])

    # Find free intervals within business hours, without buffers between events.
    free_slots = []
    previous_end = day_start
    for event in sorted_events:
        if event['end'] <= day_start or event['start'] >= day_end:
            continue
        event_start = max(event['start'], day_start)
        event_end = min(event['end'], day_end)

        if event_start - previous_end >= meeting_duration:
            free_slots.append((previous_end, event_start))
        previous_end = max(previous_end, event_end)

    # After last event
    if day_end - previous_end >= meeting_duration:
        free_slots.append((previous_end, day_end))

    # Return every valid HH:MM start, including event end times.
    available_starts = []
    for start, end in free_slots:
        last_start = end - meeting_duration
        if is_friday:
            last_start = min(last_start, friday_last_start)
        slot_start = start
        while slot_start <= last_start:
            available_starts.append(minutes_to_time(slot_start))
            slot_start += 1

    return available_starts
