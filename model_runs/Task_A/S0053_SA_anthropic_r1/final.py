
"""
Meeting slot suggestion.

`suggest_slots` returns valid meeting start times on a given day, respecting
working hours (09:00-17:00), the lunch break (12:00-13:00) and existing events.
"""

from __future__ import annotations
from typing import List, Tuple, TypedDict

try:  # Python 3.11+ allows NotRequired; keep a plain fallback otherwise.
    from typing import NotRequired  # type: ignore
except ImportError:  # pragma: no cover
    NotRequired = None  # type: ignore


class Event(TypedDict):
    start: str
    end: str


def _to_minutes(hhmm: str) -> int:
    h_str, m_str = hhmm.split(":")
    h = int(h_str)
    m = int(m_str)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"Invalid time: {hhmm}")
    return h * 60 + m


WORK_START = _to_minutes("09:00")
LUNCH_START = _to_minutes("12:00")
LUNCH_END = _to_minutes("13:00")
WORK_END = _to_minutes("17:00")
MAX_DURATION = 480

_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _to_hhmm(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def _add_busy_interval(busy: List[Tuple[int, int]], start_min: int, end_min: int) -> None:
    # Clamp to working hours and keep only overlaps.
    s = max(start_min, WORK_START)
    e = min(end_min, WORK_END)
    if e > s:
        busy.append((s, e))


def _normalize_day(day: str) -> Tuple[str, str]:
    """Return (weekday abbreviation, ISO date or '') for a day input."""
    text = day.strip()
    if len(text) == 10:
        from datetime import date as _date
        try:
            parsed = _date.fromisoformat(text)
        except ValueError:
            pass
        else:
            if parsed.isoformat() == text:
                return _WEEKDAYS[parsed.weekday()], text
    return text.lower()[:3], ""


def _event_on_other_day(event, wd: str, iso: str) -> bool:
    """True if the event carries day/date info that differs from the target day."""
    try:
        keys = event.keys()
    except AttributeError:
        return False
    for key in ("date", "day"):
        if key in keys and event[key]:
            val = str(event[key]).strip()
            ev_wd, ev_iso = _normalize_day(val)
            if ev_iso and iso:
                if ev_iso != iso:
                    return True
            elif ev_iso:
                if ev_wd != wd:
                    return True
            elif iso:
                if ev_wd != wd:
                    return True
            elif ev_wd != wd:
                return True
    return False


def suggest_slots(
    events: List[Event],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
                (optionally "day"/"date"; events for other days are ignored)
        meeting_duration: Desired meeting length in minutes
        day: Day name/abbreviation (e.g., "Mon") or ISO date ("YYYY-MM-DD")

    Returns:
        List of valid start times as "HH:MM" sorted ascending. Start times
        within a free window are spaced by the meeting duration.
    """
    if meeting_duration <= 0:
        raise ValueError("meeting_duration must be > 0")
    if meeting_duration > MAX_DURATION:
        raise ValueError("meeting_duration must not exceed 480 minutes")

    wd, iso = _normalize_day(day)
    if wd in {"sat", "sun"}:
        return []

    busy: List[Tuple[int, int]] = [(LUNCH_START, LUNCH_END)]

    for ev in events:
        if _event_on_other_day(ev, wd, iso):
            continue
        s = _to_minutes(ev["start"])
        t = _to_minutes(ev["end"])
        if t <= s:
            raise ValueError(f"Event end must be after start: {ev}")
        _add_busy_interval(busy, s, t)

    # Merge busy intervals (events may be unsorted)
    busy.sort()
    merged: List[Tuple[int, int]] = []
    for s, e in busy:
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))

    # Free intervals within the workday
    free: List[Tuple[int, int]] = []
    cursor = WORK_START
    for s, e in merged:
        if s > cursor:
            free.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < WORK_END:
        free.append((cursor, WORK_END))

    # Starts in increments of the duration within each free interval
    results: List[str] = []
    for fs, fe in free:
        start = fs
        while start + meeting_duration <= fe:
            results.append(_to_hhmm(start))
            start += meeting_duration

    return results
