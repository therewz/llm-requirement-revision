from typing import List, Dict, Optional
import datetime

WORK_START = 9 * 60     # 09:00
WORK_END = 17 * 60      # 17:00
SLOT_INTERVAL = 1       # candidate start times every minute

_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def time_to_minutes(t: str) -> int:
    try:
        h, m = t.strip().split(":")
        h, m = int(h), int(m)
    except Exception:
        raise ValueError(f"Invalid time format: {t}")
    if not (0 <= m < 60) or not (0 <= h < 24 or (h == 24 and m == 0)):
        raise ValueError(f"Invalid time format: {t}")
    return h * 60 + m


def minutes_to_time(m: int) -> str:
    h = m // 60
    m = m % 60
    return f"{h:02d}:{m:02d}"


def get_weekday_from_date(date_str: str) -> str:
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return _DAYS[dt.weekday()]
    except Exception:
        raise ValueError(f"Invalid date: {date_str}")


def _resolve_weekday(day) -> str:
    """Return a 3-letter weekday; missing/invalid day defaults to today."""
    if isinstance(day, str):
        d = day.strip()
        if len(d) == 3 and d.capitalize() in _DAYS:
            return d.capitalize()
        try:
            return get_weekday_from_date(d)
        except ValueError:
            pass
    return _DAYS[datetime.date.today().weekday()]


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: Optional[str] = None) -> List[str]:
    # Invalid meeting duration -> empty list
    if (not isinstance(meeting_duration, int) or isinstance(meeting_duration, bool)
            or meeting_duration <= 0 or meeting_duration >= 24 * 60):
        return []

    weekday = _resolve_weekday(day)
    if weekday in ("Sat", "Sun"):
        return []

    # Convert events to minutes; malformed events are ignored
    busy = []
    if isinstance(events, (list, tuple)):
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

    # Generate start times
    slots = []
    for start, end in free:
        t = start
        while t + meeting_duration <= end:
            slots.append(minutes_to_time(t))
            t += SLOT_INTERVAL

    return sorted(slots)
