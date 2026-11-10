from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """
    Suggest meeting starts on a 15-minute grid from 09:00 to 17:00.

    Events may be (start, end) pairs or dictionaries with 'start' and 'end'
    keys, using 24-hour HH:MM times. Meetings must fit within working hours
    without overlapping an event or lunch (12:00-13:00). Events wholly
    outside working hours are ignored.

    meeting_duration is a positive integer number of minutes. day is a
    three-letter day string (for example, 'Mon'); the same hours apply to
    every day. Results are HH:MM strings in ascending order.
    """
    if not isinstance(meeting_duration, int) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive integer")

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    LUNCH_START = 12 * 60
    LUNCH_END = 13 * 60
    STEP = 15

    def to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            return h * 60 + m
        except (AttributeError, TypeError, ValueError):
            raise ValueError(f"Invalid time format: {t}") from None

    def to_time_str(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    blocked = [(LUNCH_START, LUNCH_END)]
    for event in events:
        if isinstance(event, dict):
            start_time, end_time = event["start"], event["end"]
        else:
            start_time, end_time = event
        start = to_minutes(start_time)
        end = to_minutes(end_time)
        if start >= end:
            raise ValueError(f"Event start >= end: {event}")

        start = max(start, WORK_START)
        end = min(end, WORK_END)
        if start < end:
            blocked.append((start, end))

    slots = []
    latest_start = WORK_END - meeting_duration
    for slot_start in range(WORK_START, latest_start + 1, STEP):
        slot_end = slot_start + meeting_duration
        if all(slot_end <= start or slot_start >= end for start, end in blocked):
            slots.append(to_time_str(slot_start))

    return slots
