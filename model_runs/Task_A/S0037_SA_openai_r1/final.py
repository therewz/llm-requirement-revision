from typing import List, Dict


def suggest_slots(
    events: List[Dict[str, str]], meeting_duration: int, day: str
) -> List[str]:
    """
    Suggest meeting start times, sorted ascending and formatted as "HH:MM".

    Meetings must fit between 09:00 and 17:00 without overlapping lunch
    (12:00-13:00) or user events and their 15-minute post-event buffers.
    Starts are aligned to quarter hours; starts from 12:00 through 13:00
    inclusive are excluded.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}.
        meeting_duration: Desired meeting length in minutes.
        day: Date ("YYYY-MM-DD") or day abbreviation (e.g., "Mon").
            The same availability rules apply on every day.
    """
    if meeting_duration <= 0:
        return []

    work_start = 9 * 60
    work_end = 17 * 60
    lunch_start = 12 * 60
    lunch_end = 13 * 60
    time_increment = 15
    post_buffer = 15

    # OR combines overlapping busy intervals, including their buffers.
    daily_schedule = 0
    for event in events:
        daily_schedule |= _convertEventToBinary(event, post_buffer)

    # Lunch is a system event, so it has no post-event buffer.
    daily_schedule |= _convertEventToBinary(
        {"start": "12:00", "end": "13:00"}, 0
    )

    meeting_mask = _convertMeetingDurationToBinary(meeting_duration)
    output = []
    for start in range(work_start, work_end - meeting_duration + 1, time_increment):
        if lunch_start <= start <= lunch_end:
            continue
        shift = 1440 - start - meeting_duration
        if not (daily_schedule & (meeting_mask << shift)):
            output.append(f"{start // 60:02d}:{start % 60:02d}")

    return output


def _convertEventToBinary(event: Dict[str, str], postBuffer: int) -> int:
    start = int(event["start"][:2]) * 60 + int(event["start"][3:])
    end = int(event["end"][:2]) * 60 + int(event["end"][3:]) + postBuffer
    if end > 1440:
        end = 1440
    duration = end - start
    bits = (1 << duration) - 1
    bits = bits << (1440 - end)
    return bits


def _convertMeetingDurationToBinary(duration: int) -> int:
    return (1 << duration) - 1


def _convertNumberToTime(duration: int, number: int) -> str:
    minutes = 1440 - duration - number
    return f"{(minutes//60):02d}:{(minutes%60):02d}"
