from typing import List, Dict
from datetime import datetime, timedelta

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def time_to_minutes(time_str: str) -> int:
    try:
        h, m = map(int, time_str.split(":"))
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError
        return h * 60 + m
    except Exception:
        raise ValueError(f"Invalid time format: {time_str}")


def minutes_to_time(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def _now() -> datetime:
    return datetime.now()


def _resolve_day(day: str, now: datetime):
    """Return the calendar date for `day`.

    `day` is a weekday name (e.g. "Monday", "mon"), interpreted within the
    current week, or an ISO date string (YYYY-MM-DD).
    """
    if not isinstance(day, str):
        raise ValueError(f"Invalid day: {day}")
    text = day.strip().lower()
    for idx, name in enumerate(DAY_NAMES):
        if text == name or (len(text) >= 3 and name.startswith(text)):
            return (now + timedelta(days=idx - now.weekday())).date()
    try:
        return datetime.strptime(day.strip(), "%Y-%m-%d").date()
    except Exception:
        raise ValueError(f"Invalid day: {day}")


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive.")

    now = _now()
    target_date = _resolve_day(day, now)

    # Past days are never suggested
    if target_date < now.date():
        return []

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    GRANULARITY = 15

    earliest = WORK_START
    if target_date == now.date():
        # Past times are never suggested
        now_min = now.hour * 60 + now.minute + (1 if (now.second or now.microsecond) else 0)
        earliest = max(earliest, now_min)

    # Convert events to minutes
    busy_times = []
    for event in events or []:
        start = time_to_minutes(event["start"])
        end = time_to_minutes(event["end"])
        if start >= end:
            raise ValueError(f"Event start time must be before end time: {event}")
        start = max(start, WORK_START)
        end = min(end, WORK_END)
        if start < end:
            busy_times.append((start, end))
    busy_times.sort()

    # Merge overlapping events
    merged = []
    for start, end in busy_times:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    # Generate available slots
    available_slots = []
    current_time = WORK_START

    def emit(t):
        if t >= earliest:
            available_slots.append(minutes_to_time(t))

    for start, end in merged:
        while current_time + meeting_duration <= start:
            emit(current_time)
            current_time += GRANULARITY
        current_time = max(current_time, end)

    while current_time + meeting_duration <= WORK_END:
        emit(current_time)
        current_time += GRANULARITY

    return available_slots
