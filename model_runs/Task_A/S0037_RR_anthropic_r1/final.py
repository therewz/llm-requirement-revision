
import datetime
from typing import List, Dict

"""
Meeting slot suggestion.

`suggest_slots` returns a list of valid meeting start times on a given day,
respecting working hours (09:00-17:00), lunch (12:00-13:00), a 15 minute
post-meeting buffer on user events, 15 minute aligned start times, and the
Friday rule (no meeting may start after 15:00).
"""


def suggest_slots(
    events: List[Dict[str, str]], meeting_duration: int, day: str
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
        meeting_duration: Desired meeting length in minutes
        day: Date as "YYYY-MM-DD" or a three-letter day abbreviation
             (e.g., "Mon", "Tue", ... "Fri")

    Returns:
        List of valid start times as "HH:MM" sorted ascending
    """
    dailySchedule = 0
    timeIncrement = 15
    postBufferTime = 15
    output = []
    bookedTimes = events[::]

    # Add lunch hour (12:00 to 12:45 so buffer lands it exactly at 13:00)
    bookedTimes.append({"start": "12:00", "end": "12:45"})
    # Restrict time outside of work
    bookedTimes.append({"start": "00:00", "end": "08:45"})
    bookedTimes.append({"start": "17:00", "end": "23:59"})

    for booked in bookedTimes:
        dailySchedule = dailySchedule | _convertEventToBinary(booked, postBufferTime)

    # Determine if 'day' is a Friday
    is_friday = False
    try:
        dt = datetime.datetime.strptime(day, "%Y-%m-%d")
        if dt.weekday() == 4:  # Monday is 0, Friday is 4
            is_friday = True
    except ValueError:
        if day.lower().startswith("fri"):
            is_friday = True

    meeting_bits = _convertMeetingDurationToBinary(meeting_duration)

    # Iterate over 15-minute aligned start times (in minutes from midnight)
    for start in range(0, 1440 - meeting_duration + 1, timeIncrement):
        # Friday Business Rule: must not start after 15:00
        if is_friday and start > 15 * 60:
            break

        shift = 1440 - meeting_duration - start
        if not (dailySchedule & (meeting_bits << shift)):
            output.append(f"{start // 60:02d}:{start % 60:02d}")

    return output


def _convertEventToBinary(event: Dict[str, str], postBuffer: int) -> int:
    start = int(event["start"][:2]) * 60 + int(event["start"][3:])
    end = int(event["end"][:2]) * 60 + int(event["end"][3:]) + postBuffer
    if end > 1440:
        end = 1440
    duration = end - start
    if duration <= 0:
        return 0
    bits = (1 << duration) - 1
    bits = bits << (1440 - end)
    return bits


def _convertMeetingDurationToBinary(duration: int) -> int:
    return (1 << duration) - 1


def _convertNumberToTime(duration: int, number: int) -> str:
    minutes = 1440 - duration - number
    return f"{(minutes//60):02d}:{(minutes%60):02d}"
