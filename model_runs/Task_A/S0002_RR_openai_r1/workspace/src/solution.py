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
            or a canonical ISO date ("YYYY-MM-DD")

    Returns:
        List of valid start times as "HH:MM" sorted ascending, at one-minute
        resolution within 09:00-17:00. Friday starts must be no later than 15:00.
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
    FRIDAY_LAST_START_HOUR = 15

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
        """Check if a meeting slot conflicts with an existing event."""
        return not (end_minutes <= event_start or start_minutes >= event_end)

    # Convert events to minutes and filter out events outside working hours
    work_start = WORK_START_HOUR * 60
    work_end = WORK_END_HOUR * 60

    valid_events = []
    for event in events:
        event_start = time_to_minutes(event["start"])
        event_end = time_to_minutes(event["end"])
        if event_end > work_start and event_start < work_end:
            valid_events.append((event_start, event_end))

    # Generate all possible start times at the input's minute resolution.
    valid_slots = []

    # Friday-specific cutoff applies to the start, not the end, of a meeting.
    friday_cutoff = FRIDAY_LAST_START_HOUR * 60 if day == "Fri" else work_end

    for start_minutes in range(work_start, work_end):
        end_minutes = start_minutes + meeting_duration

        # Check if meeting fits within working hours
        if end_minutes > work_end:
            continue

        # Check Friday-specific constraint (15:00 itself is allowed).
        if start_minutes > friday_cutoff:
            continue

        # Check event conflicts
        conflicts = False
        for event_start, event_end in valid_events:
            if conflicts_with_event(start_minutes, end_minutes, event_start, event_end):
                conflicts = True
                break

        if not conflicts:
            valid_slots.append(minutes_to_time(start_minutes))

    return valid_slots