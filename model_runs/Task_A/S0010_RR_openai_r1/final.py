from typing import List, Dict, Tuple

def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """
    Suggest available meeting slots for a given day.

    Args:
        events: List of dicts with 'start' and 'end' times in "HH:MM" format.
        meeting_duration: Duration of the meeting in minutes.
        day: Day of the week as string, e.g., "Monday", "Friday".

    Returns:
        List of available start times in "HH:MM" format, at one-minute
        intervals within 09:00-17:00 working hours.
        Fridays: meetings cannot start after 15:00.
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
    if meeting_duration <= 0:
        return []

    def to_minutes(t: str) -> int:
        h, m = t.split(":")
        return int(h) * 60 + int(m)

    def to_hhmm(x: int) -> str:
        return f"{x // 60:02d}:{x % 60:02d}"

    WORK_START = to_minutes("09:00")
    WORK_END   = to_minutes("17:00")

    # Special Friday start-time limit (meetings may end after this time).
    FRIDAY_LIMIT = to_minutes("15:00") if day.lower() == "friday" else WORK_END

    # If meeting can't fit at all
    if WORK_START + meeting_duration > WORK_END:
        return []

    busy: List[Tuple[int, int]] = []

    # Add events clipped to working hours
    for e in events or []:
        if not isinstance(e, dict) or "start" not in e or "end" not in e:
            continue
        try:
            s = to_minutes(e["start"])
            en = to_minutes(e["end"])
        except Exception:
            continue
        if en <= s:
            continue
        if en <= WORK_START or s >= WORK_END:
            continue
        s = max(s, WORK_START)
        en = min(en, WORK_END)
        if en > s:
            busy.append((s, en))

    # Merge overlapping busy intervals
    busy.sort()
    merged: List[Tuple[int, int]] = []
    for s, en in busy:
        if not merged or s >= merged[-1][1]:
            merged.append((s, en))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], en))

    # Compute free intervals within working hours
    free: List[Tuple[int, int]] = []
    cursor = WORK_START
    for s, en in merged:
        if s > cursor:
            free.append((cursor, s))
        cursor = max(cursor, en)
    if cursor < WORK_END:
        free.append((cursor, WORK_END))

    slots: List[str] = []
    for fs, fe in free:
        t = fs
        latest_start = min(fe - meeting_duration, FRIDAY_LIMIT)
        while t <= latest_start:
            slots.append(to_hhmm(t))
            t += 1

    return slots