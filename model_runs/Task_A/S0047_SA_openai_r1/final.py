from typing import List, Dict
import datetime

WORK_START = 9 * 60     # 09:00
WORK_END = 17 * 60      # 17:00
SLOT_INTERVAL = 1      # Check every minute, including one-minute gaps.
_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def time_to_minutes(t: str) -> int:
    try:
        h, m = map(int, t.split(":"))
        if not 0 <= h < 24 or not 0 <= m < 60:
            raise ValueError
        return h * 60 + m
    except (AttributeError, TypeError, ValueError):
        raise ValueError(f"Invalid time format: {t}") from None


def minutes_to_time(m: int) -> str:
    h = m // 60
    m = m % 60
    return f"{h:02d}:{m:02d}"


def get_weekday_from_date(date_str: str) -> str:
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return _WEEKDAYS[dt.weekday()]
    except (TypeError, ValueError):
        raise ValueError(f"Invalid date: {date_str}") from None


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return all minute-aligned meeting starts during weekday work hours.

    Missing dates and invalid date strings default to today. Unrecognized
    weekday names raise ValueError. Malformed event entries are ignored.
    """
    if (not isinstance(meeting_duration, int)
            or isinstance(meeting_duration, bool)
            or not 0 < meeting_duration < 24 * 60):
        return []

    if day is None or (isinstance(day, str) and day.strip().lower() in ("", "today")):
        weekday = _WEEKDAYS[datetime.date.today().weekday()]
    elif isinstance(day, str):
        day = day.strip()
        if day.title() in _WEEKDAYS:
            weekday = day.title()
        elif "-" in day or day[:1].isdigit():
            try:
                weekday = get_weekday_from_date(day)
            except ValueError:
                weekday = _WEEKDAYS[datetime.date.today().weekday()]
        else:
            raise ValueError(f"Invalid day: {day}")
    else:
        raise ValueError(f"Invalid day: {day}")

    if weekday in ("Sat", "Sun"):
        return []

    # Ignore malformed collections and entries; valid events are clipped to work.
    busy = []
    if not isinstance(events, (list, tuple)):
        events = []
    for event in events:
        if not isinstance(event, dict):
            continue
        try:
            start = time_to_minutes(event.get("start"))
            end = time_to_minutes(event.get("end"))
        except ValueError:
            continue
        if start >= end:
            continue
        start = max(start, WORK_START)
        end = min(end, WORK_END)
        if start < end:
            busy.append((start, end))

    # Sort and merge overlapping or adjacent events.
    busy.sort()
    merged = []
    for start, end in busy:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    # Enumerate every feasible start in each free interval, already sorted.
    slots = []
    previous_end = WORK_START
    for start, end in merged + [(WORK_END, WORK_END)]:
        for minute in range(previous_end, start - meeting_duration + 1, SLOT_INTERVAL):
            slots.append(minutes_to_time(minute))
        previous_end = end
    return slots
