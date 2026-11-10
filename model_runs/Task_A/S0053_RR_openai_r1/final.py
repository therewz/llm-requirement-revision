"""Suggest non-overlapping meeting starts during working hours."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import List, Optional, Tuple, TypedDict


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
FRIDAY_CUTOFF = _to_minutes("15:00")
_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


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


def _ceil_to_grid(x: int, grid: int) -> int:
    return ((x + grid - 1) // grid) * grid


def _day_info(value: str) -> Tuple[str, Optional[str]]:
    """Return a normalized weekday/label and, if supplied, a calendar date."""
    value = value.strip().lower()
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        for weekday in _WEEKDAYS:
            if value in (weekday, weekday[:3]):
                return weekday[:3], None
        return value, None
    return _WEEKDAYS[parsed.weekday()][:3], parsed.isoformat()


def _event_matches_day(event: Mapping, weekday: str, calendar_date: Optional[str]) -> bool:
    # Undated events belong to the requested day. If both sides supply dates,
    # compare the dates rather than just their weekdays.
    for key in ("date", "day"):
        value = event.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            return False
        event_weekday, event_date = _day_info(value)
        if calendar_date is not None and event_date is not None:
            if calendar_date != event_date:
                return False
        elif weekday != event_weekday:
            return False
    return True


def suggest_slots(
    events: List[Event],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Return ascending HH:MM meeting starts, spaced by the meeting duration.

    Working periods are 09:00-12:00 and 13:00-17:00. On Fridays, starts
    after 15:00 are excluded (a start at 15:00 is allowed).

    ``day`` accepts a weekday name/abbreviation or an ISO calendar date.
    Events may include optional ``day`` or ``date`` fields; undated events
    are assumed to belong to the requested day. Unparseable events and
    events with non-positive lengths are ignored. The input is not changed.

    No regional holiday calendar is assumed. Holidays can be identified by
    ``day="holiday"`` or a matching event with ``is_holiday=True`` or
    ``holiday=True``; such days return no slots. Weekends also return none.

    Raises ValueError for a non-positive duration or one over 480 minutes.
    """
    if meeting_duration <= 0:
        raise ValueError("meeting_duration must be > 0")
    if meeting_duration > 480:
        raise ValueError("meeting_duration must not exceed 480 minutes")

    weekday, calendar_date = _day_info(day)
    if weekday in {"sat", "sun", "holiday"}:
        return []

    busy: List[Tuple[int, int]] = [(LUNCH_START, LUNCH_END)]
    for event in events:
        if not isinstance(event, Mapping):
            continue
        if not _event_matches_day(event, weekday, calendar_date):
            continue
        if event.get("is_holiday") is True or event.get("holiday") is True:
            return []
        try:
            start = _to_minutes(event["start"])
            end = _to_minutes(event["end"])
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if end <= start:
            continue
        _add_busy_interval(busy, start, end)

    # Merge existing events and lunch; touching intervals leave no free gap.
    busy.sort()
    merged: List[Tuple[int, int]] = []
    for start, end in busy:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))

    free: List[Tuple[int, int]] = []
    cursor = WORK_START
    for start, end in merged:
        if start > cursor:
            free.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < WORK_END:
        free.append((cursor, WORK_END))

    # Start at the earliest available time in each gap, then step by the
    # duration. No arbitrary grid or cooldown may hide an earlier valid slot.
    results: List[str] = []
    for start, end in free:
        last_start = end - meeting_duration
        if weekday == "fri":
            last_start = min(last_start, FRIDAY_CUTOFF)
        while start <= last_start:
            results.append(_to_hhmm(start))
            start += meeting_duration

    return results
