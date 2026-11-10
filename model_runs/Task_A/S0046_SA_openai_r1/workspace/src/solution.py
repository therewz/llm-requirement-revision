from typing import List, Dict
from datetime import datetime, timedelta


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


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Suggest starts within 09:00–17:00, using 15-minute slot spacing.

    ``day`` may be an ISO date (YYYY-MM-DD) or a full weekday name. A
    weekday name refers to its next occurrence, including today. Past
    dates and starts are excluded using the local system clock.
    """
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive.")

    now = datetime.now()
    try:
        date_obj = datetime.strptime(day, "%Y-%m-%d")
    except (TypeError, ValueError):
        weekdays = (
            "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday",
        )
        if not isinstance(day, str) or day.strip().lower() not in weekdays:
            raise ValueError(f"Invalid date or weekday: {day}")
        weekday = weekdays.index(day.strip().lower())
        date_obj = now.replace(hour=0, minute=0, second=0, microsecond=0)
        date_obj += timedelta(days=(weekday - now.weekday()) % 7)

    if date_obj.date() < now.date():
        return []

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    GRANULARITY = 15

    # Convert events to minutes.
    busy_times = []
    for event in events:
        start = time_to_minutes(event["start"])
        end = time_to_minutes(event["end"])
        if start >= end:
            raise ValueError(f"Event start time must be before end time: {event}")
        # Clip events to working hours.
        start = max(start, WORK_START)
        end = min(end, WORK_END)
        if start < end:
            busy_times.append((start, end))
    busy_times.sort()

    # Merge overlapping events.
    merged = []
    for start, end in busy_times:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    # Generate available slots.
    available_slots = []
    current_time = WORK_START

    for start, end in merged:
        while current_time + meeting_duration <= start:
            available_slots.append(current_time)
            current_time += GRANULARITY
        current_time = max(current_time, end)

    # After the last event.
    while current_time + meeting_duration <= WORK_END:
        available_slots.append(current_time)
        current_time += GRANULARITY

    return [
        minutes_to_time(start)
        for start in available_slots
        if date_obj.replace(hour=start // 60, minute=start % 60) >= now
    ]
