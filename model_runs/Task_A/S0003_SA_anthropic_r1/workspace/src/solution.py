from typing import List, Dict

def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """
    Suggest valid meeting start times for a given day.

    Parameters:
    - events: list of dictionaries with "start" and "end" times in "HH:MM" format
    - meeting_duration: desired meeting duration in minutes
    - day: the day being scheduled (not used to alter the rules)

    Returns:
    - List of valid start times as strings in "HH:MM" format (candidate starts
      are on 15-minute increments). Meetings must fit within working hours
      (09:00-17:00) and must not overlap existing events; back-to-back
      meetings are allowed. Empty list if nothing fits.
    """
    WORK_START = 9 * 60   # 09:00
    WORK_END = 17 * 60    # 17:00
    STEP_MINUTES = 15

    # Validate meeting duration
    if not isinstance(meeting_duration, int) or meeting_duration <= 0:
        return []
    if meeting_duration > (WORK_END - WORK_START):
        return []

    def to_minutes(t: str) -> int:
        hh, mm = t.split(":")
        return int(hh) * 60 + int(mm)

    def to_hhmm(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    intervals = []
    for e in events:
        try:
            s = to_minutes(e["start"])
            en = to_minutes(e["end"])
        except Exception:
            continue
        if en <= s:
            continue
        intervals.append((s, en))

    results: List[str] = []
    latest_start = WORK_END - meeting_duration

    t = WORK_START
    while t <= latest_start:
        meet_end = t + meeting_duration
        # Conflict if the time ranges overlap (touching endpoints are fine)
        if not any(t < ev_e and meet_end > ev_s for ev_s, ev_e in intervals):
            results.append(to_hhmm(t))
        t += STEP_MINUTES

    return results
