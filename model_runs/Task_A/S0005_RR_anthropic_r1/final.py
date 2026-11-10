from typing import List, Dict, Tuple

WORK_START = "09:00"
WORK_END = "17:00"
STEP_MINUTES = 15
FRIDAY_LAST_START = "15:00"  # no meeting start after 15:00 on Fridays


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

    Working hours: 09:00-17:00
    Candidate starts: every 15 minutes
    Constraints:
      - Meeting must fit within working hours
      - Meeting must not overlap any event (events are [start,end))
      - Events entirely outside working hours are ignored; partial ones are clipped
      - On Fridays, meetings must not start after 15:00
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
    if not isinstance(meeting_duration, int) or meeting_duration <= 0:
        return []

    day_start = _to_minutes(WORK_START)
    day_end = _to_minutes(WORK_END)

    if meeting_duration > (day_end - day_start):
        return []

    # Build busy intervals (clipped to working hours)
    busy: List[Tuple[int, int]] = []
    for ev in events or []:
        s = _to_minutes(ev["start"])
        e = _to_minutes(ev["end"])
        if e <= s:
            continue

        # ignore if completely outside working hours
        if e <= day_start or s >= day_end:
            continue

        # clip to working hours
        s = max(s, day_start)
        e = min(e, day_end)

        if e > s:
            busy.append((s, e))

    busy = _merge(busy)

    # Friday restriction
    if isinstance(day, str) and day.lower() == "friday":
        last_start = _to_minutes(FRIDAY_LAST_START)
    else:
        last_start = day_end

    def is_blocked(start: int) -> bool:
        end = start + meeting_duration
        # must fit in working hours
        if start < day_start or end > day_end:
            return True

        # must satisfy Friday last start restriction
        if start > last_start:
            return True

        # overlap check against busy intervals
        for bs, be in busy:
            if start < be and end > bs:
                return True
        return False

    slots: List[str] = []
    t = day_start
    while t + meeting_duration <= day_end:
        if not is_blocked(t):
            slots.append(_to_hhmm(t))
        t += STEP_MINUTES

    return slots
