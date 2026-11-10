"""Suggest meeting start times within a single day's working hours."""

import datetime
from typing import List, Dict


def suggest_slots(
    events: List[Dict[str, str]], meeting_duration: int, day: str
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
        meeting_duration: Desired meeting length in minutes
        day: An ISO date (YYYY-MM-DD) or three-letter day abbreviation

    Returns:
        List of valid start times as "HH:MM" sorted ascending. Meetings
        must fit within 09:00-17:00 and avoid lunch (12:00-13:00).
        Starts from 12:00 through 13:00 inclusive are excluded, and Friday
        starts must be no later than 15:00. Existing user events block an
        additional 15 minutes after their end; lunch has no such buffer.
    """
    work_start = 9 * 60
    work_end = 17 * 60
    if meeting_duration <= 0 or meeting_duration > work_end - work_start:
        return []

    # System events have no post-meeting buffer. Unioning occupied minutes
    # also merges overlapping user events, including their buffers.
    daily_schedule = _convertEventToBinary(
        {"start": "12:00", "end": "13:00"}, 0
    )
    for event in events:
        daily_schedule |= _convertEventToBinary(event, 15)

    try:
        is_friday = datetime.datetime.strptime(day, "%Y-%m-%d").weekday() == 4
    except ValueError:
        is_friday = day.lower().startswith("fri")

    output = []
    meeting_mask = _convertMeetingDurationToBinary(meeting_duration)
    for start in range(work_start, work_end - meeting_duration + 1, 15):
        if 12 * 60 <= start <= 13 * 60:
            continue
        if is_friday and start > 15 * 60:
            continue

        # The first bit represents the last minute of the day.
        offset = 1440 - start - meeting_duration
        if not daily_schedule & (meeting_mask << offset):
            output.append(_convertNumberToTime(meeting_duration, offset))

    return output


def _convertEventToBinary(event: Dict[str, str], postBuffer: int) -> int:
    start_hour, start_minute = map(int, event["start"].split(":"))
    end_hour, end_minute = map(int, event["end"].split(":"))
    start = start_hour * 60 + start_minute
    end = min(end_hour * 60 + end_minute + postBuffer, 1440)
    duration = end - start
    bits = (1 << duration) - 1
    bits = bits << (1440 - end)
    return bits


def _convertMeetingDurationToBinary(duration: int) -> int:
    return (1 << duration) - 1


def _convertNumberToTime(duration: int, number: int) -> str:
    minutes = 1440 - duration - number
    return f"{(minutes//60):02d}:{(minutes%60):02d}"
