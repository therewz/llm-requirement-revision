from typing import List, Dict

def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
        meeting_duration: Desired meeting length in minutes
        day: Three-letter day abbreviation (e.g., "Mon", "Tue", ... "Fri")

    Returns:
        List of valid start times as "HH:MM" sorted ascending
    """

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
    # Working hours: 9:00 AM to 5:00 PM (17:00)
    WORK_START_HOUR = 9
    WORK_END_HOUR = 17
    FRIDAY_LAST_START_HOUR = 15  # Fridays: no meeting may start after 15:00

    def time_to_minutes(time_str: str) -> int:
        """Convert "HH:MM" string to minutes since midnight."""
        hour, minute = map(int, time_str.split(":"))
        return hour * 60 + minute

    def minutes_to_time(minutes: int) -> str:
        """Convert minutes since midnight to "HH:MM" string."""
        hour = minutes // 60
        minute = minutes % 60
        return f"{hour:02d}:{minute:02d}"

    def conflicts_with_event(start_minutes: int, end_minutes: int, event_start: int, event_end: int) -> bool:
        """Check if a meeting slot overlaps an existing event (touching edges is fine)."""
        return start_minutes < event_end and end_minutes > event_start

    work_start = WORK_START_HOUR * 60
    work_end = WORK_END_HOUR * 60

    events_minutes = [
        (time_to_minutes(event["start"]), time_to_minutes(event["end"]))
        for event in events
    ]

    # Latest allowed start time
    last_start = FRIDAY_LAST_START_HOUR * 60 if day == "Fri" else work_end

    valid_slots = []
    # Generate possible start times in 15-minute intervals
    for start_minutes in range(work_start, work_end, 15):
        end_minutes = start_minutes + meeting_duration

        # Meeting must fit within working hours
        if end_minutes > work_end:
            continue

        # Friday: must not start after 15:00
        if start_minutes > last_start:
            continue

        if any(conflicts_with_event(start_minutes, end_minutes, es, ee)
               for es, ee in events_minutes):
            continue

        valid_slots.append(minutes_to_time(start_minutes))

    return valid_slots
