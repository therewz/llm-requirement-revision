from typing import List, Dict, Optional


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: Optional[str] = None
) -> List[str]:
    """
    Suggest valid meeting start times for a given day.

    Parameters:
    - events: list of dicts with 'start' and 'end' times in "HH:MM" format
    - meeting_duration: desired meeting duration in minutes
    - day: optional, accepted for compatibility; it does not affect results

    Returns:
    - List of "HH:MM" start times (15-minute steps) within working hours
      (09:00-17:00) where the meeting does not overlap any existing event.
      Empty list if none are available.
    """
    WORK_START = 9 * 60   # 09:00
    WORK_END = 17 * 60    # 17:00
    STEP = 15

    def to_minutes(time_str: str) -> int:
        h, m = map(int, time_str.strip().split(':'))
        return h * 60 + m

    def to_str(minutes: int) -> str:
        h, m = divmod(minutes, 60)
        return f"{h:02d}:{m:02d}"

    if meeting_duration <= 0:
        return []

    busy_times = []
    for event in events:
        start = to_minutes(event["start"])
        end = to_minutes(event["end"])
        if end > WORK_START and start < WORK_END:
            busy_times.append((max(start, WORK_START), min(end, WORK_END)))
    busy_times.sort()

    available_starts = []
    current_time = WORK_START

    while current_time + meeting_duration <= WORK_END:
        meeting_end = current_time + meeting_duration
        conflict_end = None

        for b_start, b_end in busy_times:
            if not (meeting_end <= b_start or current_time >= b_end):
                if conflict_end is None or b_end > conflict_end:
                    conflict_end = b_end

        if conflict_end is None:
            available_starts.append(to_str(current_time))
            current_time += STEP
        else:
            # Jump past the conflicting event, aligned to the next 15-min step
            current_time = max(conflict_end, current_time + 1)
            if current_time % STEP != 0:
                current_time += STEP - (current_time % STEP)

    return available_starts
