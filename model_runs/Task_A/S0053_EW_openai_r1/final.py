"""Suggest meeting starts within working hours, excluding lunch and busy times."""

from __future__ import annotations

from datetime import date
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


def _day_parts(value: str) -> Tuple[str, str]:
    """Return a date/label key and a weekday key for day comparisons."""
    key = value.strip().lower()
    try:
        parsed = date.fromisoformat(key)
    except ValueError:
        weekdays = {
            "monday": "mon", "tuesday": "tue", "wednesday": "wed",
            "thursday": "thu", "friday": "fri", "saturday": "sat",
            "sunday": "sun",
        }
        key = weekdays.get(key, key)
        return key, key
    return parsed.isoformat(), ("mon", "tue", "wed", "thu", "fri", "sat", "sun")[parsed.weekday()]


def suggest_slots(
    events: List[Event],
    meeting_duration: int,
    day: str
) -> List[str]:
    """
    Return ascending, non-overlapping candidate starts, in duration-sized steps.

    Events have HH:MM start/end strings and may include a ``day`` or ``date``
    field; events without either are assumed to belong to the requested day.
    Malformed events are ignored. The input list and its events are not changed.

    ``day`` accepts weekday names/abbreviations or an ISO calendar date.
    ``Holiday`` (also ``public holiday`` or ``bank holiday``) denotes a holiday;
    no jurisdiction-specific holiday calendar is assumed.

    Nonpositive durations raise ValueError. Durations over 480 minutes, weekends,
    holidays, and days without a sufficiently long free interval return [].
    """
    if meeting_duration <= 0:
        raise ValueError("meeting_duration must be > 0")
    if meeting_duration > 480:
        return []

    day_key, weekday = _day_parts(day)
    if weekday in {"sat", "sun", "holiday", "holidays", "public holiday", "bank holiday"}:
        return []

    busy: List[Tuple[int, int]] = [(LUNCH_START, LUNCH_END)]
    for event in events:
        try:
            # Prefer an explicit date over a recurring weekday label. Compare
            # complete dates when both are known, not just their weekdays.
            event_day = event.get("date") or event.get("day")
            if event_day is not None:
                event_key, event_weekday = _day_parts(event_day)
                if day_key != weekday and event_key != event_weekday:
                    if event_key != day_key:
                        continue
                elif event_weekday != weekday:
                    continue

            start = _to_minutes(event["start"])
            end = _to_minutes(event["end"])
        except (AttributeError, KeyError, TypeError, ValueError):
            # Non-parseable entries cannot supply a usable busy interval.
            continue
        if end <= start:
            continue
        _add_busy_interval(busy, start, end)

    # Merge overlapping or adjacent busy intervals, including lunch.
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

    # Start at the earliest available time in each gap. Advancing by the
    # meeting duration implements the earlier-start tie break without a
    # fixed minute grid or an extra cooldown after existing events.
    results: List[str] = []
    for start, end in free:
        while start + meeting_duration <= end:
            results.append(_to_hhmm(start))
            start += meeting_duration
    return results
