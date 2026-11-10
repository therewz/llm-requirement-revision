from typing import List, Dict, Tuple, Optional

WORK_START = "09:00"
WORK_END = "17:00"
STEP_MINUTES = 15


def _to_minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _to_hhmm(x: int) -> str:
    return f"{x // 60:02d}:{x % 60:02d}"


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: Optional[str] = None
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Working hours: 09:00-17:00
    Candidate starts: every 15 minutes
    Constraints:
      - Meeting must lie within working hours
      - Meeting must not overlap any event (events are [start, end));
        a meeting may start exactly when an event ends or end when one starts
    Returns an empty list if no slot is available.
    The `day` argument is accepted for compatibility and does not affect results.
    """
    if not isinstance(meeting_duration, int) or meeting_duration <= 0:
        return []

    day_start = _to_minutes(WORK_START)
    day_end = _to_minutes(WORK_END)

    if meeting_duration > day_end - day_start:
        return []

    busy: List[Tuple[int, int]] = []
    for ev in events or []:
        s = _to_minutes(ev["start"])
        e = _to_minutes(ev["end"])
        if e <= s:
            continue
        busy.append((s, e))

    slots: List[str] = []
    t = day_start
    while t + meeting_duration <= day_end:
        end = t + meeting_duration
        if not any(t < be and end > bs for bs, be in busy):
            slots.append(_to_hhmm(t))
        t += STEP_MINUTES

    return slots
