from datetime import datetime


def suggest_slots(events, meeting_duration, day):
    """
    Suggest meeting start times at minute precision within 09:00-17:00.

    Args:
        events (list): List of dictionaries containing 'start' and 'end' times.
        meeting_duration (int): Duration of the meeting in minutes.
        day (str): Date string (YYYY-MM-DD), used to determine the day of the week.

    Returns:
        list: Valid start times (HH:MM), with Friday starts no later than 15:00.
    """
    # Define working hours.
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

    # Only existing events block time within the working day.
    blocked_intervals = []
    for event in events:
        start = time_to_minutes(event['start'])
        end = time_to_minutes(event['end'])
        blocked_intervals.append((start, end))

    # Sort intervals by start time
    blocked_intervals.sort(key=lambda x: x[0])

    valid_slots = []

    # Check every minute so starts need not fall on a quarter hour.
    current_time = work_start_min
    while current_time + meeting_duration <= work_end_min:
        meeting_start = current_time
        meeting_end = current_time + meeting_duration

        # Apply Friday restriction
        if is_friday and meeting_start > friday_last_start_min:
            break  # No meeting can start after 15:00 on Friday

        # Check for overlaps with blocked intervals
        is_valid = True
        for b_start, b_end in blocked_intervals:
            if meeting_start < b_end and meeting_end > b_start:
                is_valid = False
                break

        if is_valid:
            valid_slots.append(minutes_to_time(meeting_start))

        current_time += 1

    return valid_slots
