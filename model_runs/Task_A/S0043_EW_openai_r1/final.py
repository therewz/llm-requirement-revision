from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """
    Suggest valid meeting start times for a given day.

    Args:
        events: List of events as (start, end) pairs or dictionaries with
            'start' and 'end', in HH:MM format.
        meeting_duration (int): Meeting duration in minutes.
        day (str): Three-letter day string, such as 'Mon' or 'Fri'.
            The same scheduling rules apply every day.

    Returns:
        List[str]: Valid start times in HH:MM format, ascending.
    """
    # --- Input validation ---
    if not isinstance(meeting_duration, int) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive integer")

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    LUNCH_START = 12 * 60
    LUNCH_END = 13 * 60
    STEP = 15

    def to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            return h * 60 + m
        except:
            raise ValueError(f"Invalid time format: {t}")

    def to_time_str(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    # --- Build blocked intervals ---
    blocked = []

    for e in events:
        if isinstance(e, dict):
            start = to_minutes(e["start"])
            end = to_minutes(e["end"])
        else:
            start_time, end_time = e
            start = to_minutes(start_time)
            end = to_minutes(end_time)
        if start >= end:
            raise ValueError(f"Event start >= end: {e}")

        # Clamp to work hours
        start = max(start, WORK_START)
        end = min(end, WORK_END)

        if end <= WORK_START or start >= WORK_END:
            continue

        blocked.append((start, end))

    # Add lunch break
    blocked.append((LUNCH_START, LUNCH_END))

    # --- Determine candidate slots ---
    slots = []
    current = WORK_START
    latest_start = WORK_END - meeting_duration

    while current <= latest_start:
        slot_start = current
        slot_end = current + meeting_duration

        conflict = False
        for b_start, b_end in blocked:
            if not (slot_end <= b_start or slot_start >= b_end):
                conflict = True
                break

        if not conflict:
            slots.append(to_time_str(slot_start))

        current += STEP

    return slots
