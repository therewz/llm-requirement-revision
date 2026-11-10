from typing import List, Dict
from datetime import datetime

WORK_START = 9 * 60
WORK_END = 17 * 60
LUNCH_START = 12 * 60
LUNCH_END = 13 * 60
INTERVAL = 15  # 15-minute increments
FRIDAY_CUTOFF = 15 * 60  # latest allowed start on Fridays: 15:00


def to_minutes(t: str) -> int:
    try:
        h, m = map(int, t.split(":"))
    except Exception:
        raise ValueError(f"Invalid time format: {t}")
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"Invalid time value: {t}")
    return h * 60 + m


def to_time_str(m: int) -> str:
    h, mi = divmod(m, 60)
    return f"{h:02d}:{mi:02d}"


def validate_date(day: str):
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except Exception:
        raise ValueError(f"Invalid date: {day}")


def is_friday(day: str) -> bool:
    dt = datetime.strptime(day, "%Y-%m-%d")
    return dt.weekday() == 4  # Monday=0, Friday=4


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    validate_date(day)

    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    busy = [(LUNCH_START, LUNCH_END)]
    for e in events:
        start = to_minutes(e["start"])
        end = to_minutes(e["end"])
        if start >= end:
            raise ValueError(f"Event start >= end: {e}")
        busy.append((start, end))

    friday = is_friday(day)
    last_start = WORK_END - meeting_duration
    if friday:
        last_start = min(last_start, FRIDAY_CUTOFF)

    slots = []
    t = WORK_START
    while t <= last_start:
        t_end = t + meeting_duration
        # overlap if the intervals intersect (touching endpoints is fine)
        if all(t_end <= s or t >= e for s, e in busy):
            slots.append(to_time_str(t))
        t += INTERVAL

    return slots
