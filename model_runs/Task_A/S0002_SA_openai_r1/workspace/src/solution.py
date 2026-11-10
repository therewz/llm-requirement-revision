from typing import List, Dict


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Suggest meeting start times at 15-minute intervals from 09:00 to 17:00.

    Args:
        events: Events for the day, with keys {"start": "HH:MM", "end": "HH:MM"}.
        meeting_duration: Desired meeting length in minutes.
        day: Day label, retained for compatibility. Working hours are the same
            for every day.

    Returns:
        Valid start times as "HH:MM", sorted ascending. Meetings must finish
        by 17:00 and may start or end exactly when another event ends or starts.
    """
    def time_to_minutes(time_str: str) -> int:
        """Convert an HH:MM string to minutes since midnight."""
        hour, minute = map(int, time_str.split(":"))
        return hour * 60 + minute

    def minutes_to_time(minutes: int) -> str:
        """Convert minutes since midnight to an HH:MM string."""
        hour, minute = divmod(minutes, 60)
        return f"{hour:02d}:{minute:02d}"

    work_start = 9 * 60
    work_end = 17 * 60

    # Events outside working hours cannot block any proposed meeting.
    valid_events = []
    for event in events:
        event_start = time_to_minutes(event["start"])
        event_end = time_to_minutes(event["end"])
        if event_end > work_start and event_start < work_end:
            valid_events.append((event_start, event_end))

    valid_slots = []
    for start_minutes in range(work_start, work_end, 15):
        end_minutes = start_minutes + meeting_duration
        if end_minutes > work_end:
            continue

        if any(
            start_minutes < event_end and end_minutes > event_start
            for event_start, event_end in valid_events
        ):
            continue

        valid_slots.append(minutes_to_time(start_minutes))

    return valid_slots
