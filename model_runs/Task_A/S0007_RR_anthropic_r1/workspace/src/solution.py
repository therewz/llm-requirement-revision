
from datetime import datetime

def suggest_slots(events, meeting_duration, day):
    """
    Suggests meeting slots for a given day.

    Args:
        events (list): List of dictionaries containing 'start' and 'end' times.
        meeting_duration (int): Duration of the meeting in minutes.
        day (str): Date string (YYYY-MM-DD), used to determine the day of the week.

    Returns:
        list: A list of valid start times (HH:MM) strings.
    """
    # Define working hours
    WORK_START = "09:00"
    WORK_END = "17:00"

    # Friday meeting latest start restriction
    FRIDAY_LAST_START = "15:00"

    # Helper to convert HH:MM to minutes from midnight
    def time_to_minutes(t_str):
        h, m = map(int, t_str.split(':'))
        return h * 60 + m

    # Helper to convert minutes to HH:MM
    def minutes_to_time(minutes):
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}:{m:02d}"

    # Convert constants to minutes
    work_start_min = time_to_minutes(WORK_START)
    work_end_min = time_to_minutes(WORK_END)
    friday_last_start_min = time_to_minutes(FRIDAY_LAST_START)

    # Determine if the day is a Friday
    dt = datetime.strptime(day, "%Y-%m-%d")
    is_friday = dt.weekday() == 4  # Monday=0, ..., Friday=4

    # Blocked intervals (in minutes) from existing events
    blocked_intervals = []
    for event in events:
        start = time_to_minutes(event['start'])
        end = time_to_minutes(event['end'])
        blocked_intervals.append((start, end))

    blocked_intervals.sort(key=lambda x: x[0])

    valid_slots = []

    # Iterate through the working day in 15-minute increments
    current_time = work_start_min
    while current_time + meeting_duration <= work_end_min:
        meeting_start = current_time
        meeting_end = current_time + meeting_duration

        # Friday restriction: no meeting may start after 15:00
        if is_friday and meeting_start > friday_last_start_min:
            break

        # Check for overlaps with blocked intervals
        is_valid = True
        for b_start, b_end in blocked_intervals:
            if meeting_start < b_end and meeting_end > b_start:
                is_valid = False
                break

        if is_valid:
            valid_slots.append(minutes_to_time(meeting_start))

        current_time += 15

    return valid_slots
