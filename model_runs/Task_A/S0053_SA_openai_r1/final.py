"""Suggest nonconflicting meeting times during the working day."""

from __future__ import annotations

from collections.abc import Mapping
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

# No holiday jurisdiction is implied. Populate this with ISO dates (or day
# labels) for the calendar in use. The explicit day label "holiday" also works.
HOLIDAYS: set[str] = set()

_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_WEEKDAY_NAMES = dict(zip(
    ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"),
    _WEEKDAYS,
))


def _day_details(value: str) -> Tuple[date | None, str]:
    label = value.strip().lower()
    try:
        calendar_date = date.fromisoformat(label)
    except ValueError:
        return None, _WEEKDAY_NAMES.get(label, label)
    return calendar_date, _WEEKDAYS[calendar_date.weekday()]


def _same_day(left: Tuple[date | None, str], right: Tuple[date | None, str]) -> bool:
    # Distinct dates must not match merely because their weekdays match.
    if left[0] is not None and right[0] is not None:
        return left[0] == right[0]
    return left[1] == right[1]


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
    Return ascending, duration-spaced meeting starts within each free interval.

    ``day`` accepts a weekday name/abbreviation or an ISO date. Holidays are
    supplied through ``HOLIDAYS`` or the explicit day label "holiday"; no
    country-specific holiday calendar is assumed.

    Events contain HH:MM ``start`` and ``end`` values. Optional ``day``/``date``
    fields restrict an event to that day; undated events apply to the requested
    day. Events marked ``peaceable=False`` and malformed events are ignored.
    The input list and its events are never modified.

    Durations must be positive and at most 480 minutes; otherwise ValueError
    is raised. A valid duration that cannot fit returns an empty list.
    """
    if meeting_duration <= 0 or meeting_duration > 480:
        raise ValueError("meeting_duration must be between 1 and 480 minutes")

    scheduled_day = _day_details(day)
    if scheduled_day[1] in {"sat", "sun", "holiday"}:
        return []
    if any(_day_details(holiday) == scheduled_day for holiday in HOLIDAYS):
        return []

    busy: List[Tuple[int, int]] = [(LUNCH_START, LUNCH_END)]
    for event in events:
        if not isinstance(event, Mapping) or event.get("peaceable", True) is False:
            continue
        try:
            if any(
                event.get(key) is not None
                and not _same_day(_day_details(event[key]), scheduled_day)
                for key in ("day", "date")
            ):
                continue
            start = _to_minutes(event["start"])
            end = _to_minutes(event["end"])
        except (KeyError, TypeError, ValueError, AttributeError):
            # Unparseable events cannot define a usable busy interval.
            continue
        if end <= start:
            continue
        _add_busy_interval(busy, start, end)

    # Merge busy intervals; pre-existing overlaps are allowed.
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

    # Greedily choose the earliest start in each gap, then advance by the
    # duration. This also resolves nearby alternatives in favor of the earlier
    # start, without imposing an unrelated clock grid.
    results: List[str] = []
    for start, end in free:
        while start + meeting_duration <= end:
            results.append(_to_hhmm(start))
            start += meeting_duration
    return results
