from typing import List, Dict, Optional
import datetime

WORK_START = 9 * 60     # 09:00
WORK_END = 17 * 60      # 17:00
SLOT_INTERVAL = 15      # 15-minute increments
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def time_to_minutes(t: str) -> int:
    try:
        h, m = map(int, t.split(":"))
        if not (0 <= h <= 24 and 0 <= m < 60):
            raise ValueError
        return h * 60 + m
    except Exception:
        raise ValueError(f"Invalid time format: {t}")


def minutes_to_time(m: int) -> str:
    h = m // 60
    m = m % 60
    return f"{h:02d}:{m:02d}"


def get_weekday_from_date(date_str: str) -> str:
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%a")  # 'Mon', 'Tue', etc.
    except Exception:
        raise ValueError(f"Invalid date: {date_str}")


def _today_weekday() -> str:
    return WEEKDAYS[datetime.date.today().weekday()]


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: Optional[str] = None) -> List[str]:
    # Invalid meeting duration -> empty list
    if (not isinstance(meeting_duration, int) or isinstance(meeting_duration, bool)
            or meeting_duration <= 0 or meeting_duration >= 24 * 60):
        return []

    # Determine weekday: missing/invalid date defaults to today
    if not isinstance(day, str) or not day.strip():
        weekday = _today_weekday()
    else:
        day = day.strip()
        if len(day) == 3:
            weekday = day.capitalize()
            if weekday not in WEEKDAYS:
                raise ValueError(f"Invalid day: {day}")
        else:
            try:
                weekday = get_weekday_from_date(day)
            except ValueError:
                weekday = _today_weekday()

    if weekday in ("Sat", "Sun"):
        return []

    # Convert events to minutes and clip to work hours; ignore malformed ones
    busy = []
    if not isinstance(events, (list, tuple)):
        events = []
    for e in events:
        if not isinstance(e, dict):
            continue
        try:
            start = time_to_minutes(e["start"])
            end = time_to_minutes(e["end"])
        except Exception:
            continue
        if start >= end:
            continue
        start = max(start, WORK_START)
        end = min(end, WORK_END)
        if start < end:
            busy.append((start, end))

    # Sort and merge overlapping intervals
    busy.sort()
    merged = []
    for start, end in busy:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    # Find free intervals
    free = []
    prev_end = WORK_START
    for start, end in merged:
        if start - prev_end >= meeting_duration:
            free.append((prev_end, start))
        prev_end = end
    if WORK_END - prev_end >= meeting_duration:
        free.append((prev_end, WORK_END))

    # Candidate starts: free-interval start plus 15-minute grid times
    slots = set()
    for start, end in free:
        slots.add(start)
        t = ((start + SLOT_INTERVAL - 1) // SLOT_INTERVAL) * SLOT_INTERVAL
        while t + meeting_duration <= end:
            slots.add(t)
            t += SLOT_INTERVAL

    return [minutes_to_time(t) for t in sorted(slots) if t + meeting_duration <= WORK_END]
