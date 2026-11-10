
"""
Meeting slot suggestion.

`suggest_slots` returns a list of valid meeting start times on a given day,
respecting working hours (09:00-17:00, no 12:00-13:00 lunch), existing events,
and the Friday rule (no meeting may start after 15:00 on Fridays).
"""

from __future__ import annotations
from typing import List, Tuple, TypedDict


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
FRIDAY_LATEST_START = _to_minutes("15:00")
MAX_DURATION = 480


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


def suggest_slots(
    events: List[Event],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Suggest possible meeting start times for a given day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
        meeting_duration: Desired meeting length in minutes
        day: Three-letter day abbreviation (e.g., "Mon", "Tue", ... "Fri")

    Returns:
        List of valid start times as "HH:MM" sorted ascending. Candidate
        starts are spaced by the meeting duration within each free interval.
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
                day = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[_parsed_calendar_input.weekday()]

    if meeting_duration <= 0:
        raise ValueError("meeting_duration must be > 0")
    if meeting_duration > MAX_DURATION:
        return []

    d = day.strip().lower()
    if d in {"sat", "saturday", "sun", "sunday"}:
        return []

    is_friday = d in {"fri", "friday"}

    busy: List[Tuple[int, int]] = []

    for e in events:
        s = _to_minutes(e["start"])
        t = _to_minutes(e["end"])
        if t <= s:
            raise ValueError(f"Event end must be after start: {e}")
        _add_busy_interval(busy, s, t)

    # Lunch is always blocked.
    _add_busy_interval(busy, LUNCH_START, LUNCH_END)

    # Merge busy intervals (events may be unsorted)
    busy.sort()
    merged: List[Tuple[int, int]] = []
    for s, e in busy:
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))

    # Compute free intervals within workday
    free: List[Tuple[int, int]] = []
    cursor = WORK_START
    for s, e in merged:
        if s > cursor:
            free.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < WORK_END:
        free.append((cursor, WORK_END))

    # Enumerate valid starts, in increments of the meeting duration
    results: List[str] = []
    for fs, fe in free:
        start = fs
        while start + meeting_duration <= fe:
            if is_friday and start > FRIDAY_LATEST_START:
                break
            results.append(_to_hhmm(start))
            start += meeting_duration

    return results
