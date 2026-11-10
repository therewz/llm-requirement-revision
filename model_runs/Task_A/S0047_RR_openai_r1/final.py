from typing import List, Dict
import datetime

WORK_START = 9 * 60     # 09:00
WORK_END = 17 * 60      # 17:00
SLOT_INTERVAL = 1       # Consider every minute, including short free gaps
FRIDAY_LAST_SLOT = 15 * 60  # 15:00


def time_to_minutes(t: str) -> int:
    if not isinstance(t, str) or len(t) != 5 or t[2] != ":":
        raise ValueError(f"Invalid time format: {t}")
    hours, minutes = t.split(":")
    if not hours.isdigit() or not minutes.isdigit():
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
        raise ValueError(f"Invalid date: {date_str}")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Suggest all minute-aligned starts within working hours.

    Invalid weekday abbreviations raise ValueError. Missing or invalid dates
    default to today, and malformed events are ignored.
    """
    if (isinstance(meeting_duration, bool)
            or not isinstance(meeting_duration, int)
            or not 0 < meeting_duration < 24 * 60):
        return []

    # A three-letter day must be a valid weekday abbreviation. Other values
    # are treated as dates, with missing/invalid dates defaulting to today.
    if isinstance(day, str) and len(day) == 3:
        weekday = day.title()
        if weekday not in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
            raise ValueError(f"Invalid day: {day}")
    else:
        try:
            weekday = get_weekday_from_date(day)
        except ValueError:
            weekday = datetime.date.today().strftime("%a")

    if weekday in ("Sat", "Sun"):
        return []

    # Convert well-formed events to minutes and clip to work hours.
    busy = []
    for e in events if isinstance(events, (list, tuple)) else ():
        if not isinstance(e, dict):
            continue
        try:
            start = time_to_minutes(e.get("start"))
            end = time_to_minutes(e.get("end"))
        except ValueError:
            continue
        if start >= end:
            continue
        start = max(start, WORK_START)
        end = min(end, WORK_END)
        if start < end:
            busy.append((start, end))

    # Sort and merge overlapping or adjacent intervals.
    busy.sort()
    merged = []
    for start, end in busy:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    free = []
    prev_end = WORK_START
    for start, end in merged:
        if start - prev_end >= meeting_duration:
            free.append((prev_end, start))
        prev_end = end
    if WORK_END - prev_end >= meeting_duration:
        free.append((prev_end, WORK_END))

    slots = []
    for start, end in free:
        last_start = end - meeting_duration
        if weekday == "Fri":
            last_start = min(last_start, FRIDAY_LAST_SLOT)
        for t in range(start, last_start + 1, SLOT_INTERVAL):
            slots.append(minutes_to_time(t))
    return slots
