from typing import List, Dict


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Suggest meeting start times at one-minute intervals within 09:00–17:00.

    Parameters:
    - events: list of dicts with 'start' and 'end' times in "HH:MM" format
    - meeting_duration: desired meeting duration in minutes
    - day: day label, retained for compatibility; working hours apply every day

    Returns:
    - Chronologically ordered start times that fit without overlapping events.
      Nonpositive durations or a lack of suitable slots produce an empty list.
    """
    WORK_START = 9 * 60   # 09:00
    WORK_END = 17 * 60    # 17:00

    if meeting_duration <= 0 or meeting_duration > WORK_END - WORK_START:
        return []

    def to_minutes(time_str: str) -> int:
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    def to_str(minutes: int) -> str:
        h, m = divmod(minutes, 60)
        return f"{h:02d}:{m:02d}"

    busy_times = []
    for event in events:
        start = max(to_minutes(event["start"]), WORK_START)
        end = min(to_minutes(event["end"]), WORK_END)
        if start < end:
            busy_times.append((start, end))
    busy_times.sort()

    available_starts = []
    current_time = WORK_START

    while current_time + meeting_duration <= WORK_END:
        meeting_end = current_time + meeting_duration
        conflict_end = None

        for busy_start, busy_end in busy_times:
            if current_time < busy_end and meeting_end > busy_start:
                conflict_end = busy_end
                break

        if conflict_end is None:
            available_starts.append(to_str(current_time))
            current_time += 1
        else:
            current_time = conflict_end

    return available_starts
