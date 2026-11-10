
def suggest_slots(events, meeting_duration, day):
    """
    Suggests meeting slots for a given day.

    Args:
        events (list): List of dictionaries containing 'start' and 'end' times.
        meeting_duration (int): Duration of the meeting in minutes.
        day (str): Date string (YYYY-MM-DD) for the day being scheduled.

    Returns:
        list: A list of valid start times (HH:MM) strings.
    """
    # Define working hours and lunch break
    WORK_START = "09:00"
    WORK_END = "17:00"
    LUNCH_START = "12:00"
    LUNCH_END = "13:00"

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

    # Create a list of blocked intervals (in minutes)
    blocked_intervals = []
    
    # Add lunch break
    blocked_intervals.append((time_to_minutes(LUNCH_START), time_to_minutes(LUNCH_END)))
    
    # Add existing events
    for event in events:
        start = time_to_minutes(event['start'])
        end = time_to_minutes(event['end'])
        blocked_intervals.append((start, end))
    
    # Sort intervals by start time
    blocked_intervals.sort(key=lambda x: x[0])
    
    valid_slots = []
    
    # Iterate through the working day in 15-minute increments
    current_time = work_start_min
    while current_time + meeting_duration <= work_end_min:
        meeting_start = current_time
        meeting_end = current_time + meeting_duration

        # Check for overlaps with blocked intervals
        is_valid = True
        for b_start, b_end in blocked_intervals:
            if meeting_start < b_end and meeting_end > b_start:
                is_valid = False
                break
        
        if is_valid:
            valid_slots.append(minutes_to_time(meeting_start))
        
        # Advance by 15 minutes
        current_time += 15
    
    return valid_slots