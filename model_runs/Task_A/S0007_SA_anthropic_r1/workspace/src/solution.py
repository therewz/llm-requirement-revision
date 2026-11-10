
def suggest_slots(events, meeting_duration, day=None):
    """
    Suggests meeting slots for a day.

    Args:
        events (list): List of dictionaries containing 'start' and 'end' times (HH:MM).
        meeting_duration (int): Duration of the meeting in minutes.
        day (str, optional): Date string (YYYY-MM-DD). Not needed for the
            calculation; accepted for backward compatibility.

    Returns:
        list: A list of valid start times (HH:MM) strings. Empty if none fit.
    """
    WORK_START = "09:00"
    WORK_END = "17:00"
    STEP = 15  # candidate start times every 15 minutes

    def time_to_minutes(t_str):
        h, m = map(int, t_str.strip().split(':'))
        return h * 60 + m

    def minutes_to_time(minutes):
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    work_start_min = time_to_minutes(WORK_START)
    work_end_min = time_to_minutes(WORK_END)

    if meeting_duration is None or meeting_duration <= 0:
        return []

    blocked_intervals = []
    for event in events or []:
        blocked_intervals.append(
            (time_to_minutes(event['start']), time_to_minutes(event['end']))
        )

    valid_slots = []
    current_time = work_start_min
    while current_time + meeting_duration <= work_end_min:
        meeting_end = current_time + meeting_duration
        if all(not (current_time < b_end and meeting_end > b_start)
               for b_start, b_end in blocked_intervals):
            valid_slots.append(minutes_to_time(current_time))
        current_time += STEP

    return valid_slots
