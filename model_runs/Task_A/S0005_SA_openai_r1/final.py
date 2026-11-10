from typing import List, Dict, Tuple

WORK_START = "09:00"
WORK_END = "17:00"
STEP_MINUTES = 15


def _to_minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _to_hhmm(x: int) -> str:
    return f"{x // 60:02d}:{x % 60:02d}"


def _merge(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not intervals:
        return []
    intervals.sort()
    out = [intervals[0]]
    for s, e in intervals[1:]:
        ps, pe = out[-1]
        if s <= pe:  # overlap/adjacent
            out[-1] = (ps, max(pe, e))
        else:
            out.append((s, e))
    return out


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Working hours: 09:00-17:00.
    Candidate starts: every 15 minutes.
    Meetings must fit entirely within working hours and must not overlap
    any event. Events are [start, end), so meetings may touch their boundaries.
    Events outside working hours are ignored; partial ones are clipped.
    The day argument is retained for compatibility; all days use the same rules.
    """
    if not isinstance(meeting_duration, int) or meeting_duration <= 0:
        return []

    day_start = _to_minutes(WORK_START)
    day_end = _to_minutes(WORK_END)

    if meeting_duration > (day_end - day_start):
        return []

    # Build busy intervals, clipped to working hours.
    busy: List[Tuple[int, int]] = []
    for ev in events or []:
        s = _to_minutes(ev["start"])
        e = _to_minutes(ev["end"])
        if e <= s:
            continue

        if e <= day_start or s >= day_end:
            continue

        s = max(s, day_start)
        e = min(e, day_end)
        busy.append((s, e))

    busy = _merge(busy)

    def overlaps_busy(start: int) -> bool:
        end = start + meeting_duration
        for bs, be in busy:
            if start < be and end > bs:
                return True
        return False

    slots: List[str] = []
    t = day_start
    while t + meeting_duration <= day_end:
        if not overlaps_busy(t):
            slots.append(_to_hhmm(t))
        t += STEP_MINUTES

    return slots
