from typing import List, Dict
import datetime

WORK_START = 9 * 60     # 09:00
WORK_END = 17 * 60      # 17:00
SLOT_INTERVAL = 1       # Consider every minute, including short free gaps.


def time_to_minutes(t: str) -> int:
    if not isinstance(t, str) or len(t) != 5 or t[2] != ":":
        raise ValueError(f"Invalid time format: {t}")
    hours, minutes = t.split(":")
    if not hours.isdecimal() or not minutes.isdecimal():
        raise ValueError(f"Invalid time format: {t}")
    h, m = int(hours), int(minutes)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"Invalid time format: {t}")
    return h * 60 + m


def minutes_to_time(m: int) -> str:
    h = m // 60
    m = m % 60
    return f"{h:02d}:{m:02d}"


def get_weekday_from_date(date_str: str) -> str:
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%a")  # 'Mon', 'Tue', etc.
    except (TypeError, ValueError):
        raise ValueError(f"Invalid date: {date_str}") from None


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    if (not isinstance(meeting_duration, int)
            or isinstance(meeting_duration, bool)
            or not 0 < meeting_duration < 24 * 60):
        return []

    # A three-letter input denotes a weekday and must be a valid one.
    # Missing or invalid dates fall back to today.
    if isinstance(day, str):
        day = day.strip()
    if not day or (isinstance(day, str) and day.lower() == "today"):
        weekday = datetime.datetime.today().strftime("%a")
    elif isinstance(day, str) and len(day) == 3:
        weekday = day.title()
        if weekday not in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
            raise ValueError(f"Invalid day: {day}")
    else:
        try:
            weekday = get_weekday_from_date(day)
        except ValueError:
            weekday = datetime.datetime.today().strftime("%a")

    if weekday in ("Sat", "Sun"):
        return []

    # Ignore malformed event collections and entries, and clip valid events
    # to working hours before merging them.
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

    busy.sort()
    merged = []
    for start, end in busy:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    # Enumerate every fitting start in each free interval. Meetings may end
    # exactly at an event's start or at the end of the working day.
    slots = []
    prev_end = WORK_START
    for start, end in merged:
        for minute in range(prev_end, start - meeting_duration + 1, SLOT_INTERVAL):
            slots.append(minutes_to_time(minute))
        prev_end = end
    for minute in range(prev_end, WORK_END - meeting_duration + 1, SLOT_INTERVAL):
        slots.append(minutes_to_time(minute))

    return slots
