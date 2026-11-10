from typing import List, Dict, Optional
import datetime

WORK_START = 9 * 60     # 09:00
WORK_END = 17 * 60      # 17:00
FRIDAY_LAST_START = 15 * 60  # Friday meetings must not start after 15:00
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def time_to_minutes(t: str) -> int:
    try:
        h, m = t.strip().split(":")
        h, m = int(h), int(m)
    except Exception:
        raise ValueError(f"Invalid time format: {t}")
    if not (0 <= h <= 24 and 0 <= m <= 59) or (h == 24 and m != 0):
        raise ValueError(f"Invalid time format: {t}")
    return h * 60 + m


def minutes_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _weekday_of(day: Optional[str]) -> str:
    """Return a 3-letter weekday. Missing/invalid dates default to today.
    A 3-letter string that is not a weekday abbreviation raises ValueError."""
    if isinstance(day, str):
        d = day.strip()
        if len(d) == 3:
            name = d.capitalize()
            if name in WEEKDAYS:
                return name
            raise ValueError(f"Invalid day: {day}")
        try:
            return datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%a")
        except ValueError:
            pass
    return datetime.date.today().strftime("%a")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str = None) -> List[str]:
    # Invalid duration -> empty list
    if (not isinstance(meeting_duration, int) or isinstance(meeting_duration, bool)
            or meeting_duration <= 0 or meeting_duration >= 24 * 60):
        return []

    weekday = _weekday_of(day)
    if weekday in ("Sat", "Sun"):
        return []

    # Collect valid events; ignore malformed ones
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

    # Merge overlapping intervals
    busy.sort()
    merged = []
    for start, end in busy:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    # Free intervals
    free = []
    prev_end = WORK_START
    for start, end in merged:
        if start - prev_end >= meeting_duration:
            free.append((prev_end, start))
        prev_end = max(prev_end, end)
    if WORK_END - prev_end >= meeting_duration:
        free.append((prev_end, WORK_END))

    # Every minute at which the meeting fits is a valid start time
    slots = []
    for start, end in free:
        last_start = end - meeting_duration
        if weekday == "Fri":
            last_start = min(last_start, FRIDAY_LAST_START)
        for t in range(start, last_start + 1):
            slots.append(minutes_to_time(t))

    return sorted(slots)
