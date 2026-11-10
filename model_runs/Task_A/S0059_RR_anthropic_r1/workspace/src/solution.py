from typing import List, Dict
from datetime import datetime

WORK_START = 9 * 60
WORK_END = 17 * 60
GRANULARITY = 15
FRIDAY_CUTOFF = 15 * 60  # Friday meetings must not start after 15:00


def _parse_time(value: str) -> int:
    try:
        h, m = value.strip().split(':')
        h, m = int(h), int(m)
    except Exception:
        raise ValueError("Invalid time format: %r" % (value,))
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("Invalid time value: %r" % (value,))
    return h * 60 + m


def _is_friday(day) -> bool:
    if not isinstance(day, str):
        return False
    d = day.strip()
    if d.lower() in ("friday", "fri"):
        return True
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(d, fmt).weekday() == 4
        except ValueError:
            continue
    return False


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    busy = []
    for e in events or []:
        start = _parse_time(e['start'])
        end = _parse_time(e['end'])
        if start >= end:
            raise ValueError("Event start time must be before end time")
        busy.append((start, end))

    latest_start = WORK_END - meeting_duration
    if _is_friday(day):
        latest_start = min(latest_start, FRIDAY_CUTOFF)

    slots = []
    s = WORK_START
    while s <= latest_start:
        end = s + meeting_duration
        if all(end <= bs or s >= be for bs, be in busy):
            slots.append(f"{s // 60:02d}:{s % 60:02d}")
        s += GRANULARITY
    return slots
