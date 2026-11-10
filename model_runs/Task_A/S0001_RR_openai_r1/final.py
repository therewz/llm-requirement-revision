from typing import List, Dict

def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Suggest valid meeting start times for a given day.

    Parameters:
    - events: list of dicts with 'start' and 'end' times in "HH:MM" format
    - meeting_duration: desired meeting duration in minutes
    - day: weekday name (case-insensitive) or an ISO date (YYYY-MM-DD)

    Returns:
    - Available start times at one-minute resolution within 09:00–17:00.
      Friday meetings must start no later than 15:00.
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
                day = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')[_parsed_calendar_input.weekday()]

    WORK_START = 9 * 60   # 09:00
    WORK_END = 17 * 60    # 17:00
    FRIDAY_START_LIMIT = 15 * 60  # 15:00

    def to_minutes(time_str: str) -> int:
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    def to_str(minutes: int) -> str:
        h, m = divmod(minutes, 60)
        return f"{h:02d}:{m:02d}"

    # Build and sort the busy list, clipping events to working hours.
    busy_times = []
    for event in events:
        start = to_minutes(event["start"])
        end = to_minutes(event["end"])
        if end > WORK_START and start < WORK_END:
            busy_times.append((max(start, WORK_START), min(end, WORK_END)))
    busy_times.sort()

    latest_start = WORK_END - meeting_duration
    if day.lower() == "friday":
        latest_start = min(latest_start, FRIDAY_START_LIMIT)

    available_starts = []
    current_time = WORK_START

    while current_time <= latest_start:
        meeting_end = current_time + meeting_duration
        conflict_end = -1

        for b_start, b_end in busy_times:
            if not (meeting_end <= b_start or current_time >= b_end):
                conflict_end = b_end
                break

        if conflict_end == -1:
            available_starts.append(to_str(current_time))
            current_time += 1
        else:
            # No start before this busy period ends can avoid the conflict.
            current_time = conflict_end

    return available_starts
