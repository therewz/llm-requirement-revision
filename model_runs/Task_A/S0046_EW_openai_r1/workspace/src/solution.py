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
    if not isinstance(meeting_duration, int) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be a positive integer in minutes.")

    now = datetime.now()
    # Accept explicit dates, or the next occurrence (including today) of a weekday.
    weekdays = (
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    )
    try:
        date_obj = datetime.strptime(day, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        if not isinstance(day, str) or day.lower() not in weekdays:
            raise ValueError(f"Invalid date: {day}")
        days_ahead = (weekdays.index(day.lower()) - now.weekday()) % 7
        date_obj = now.date() + timedelta(days=days_ahead)

    if date_obj < now.date():
        return []

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    GRANULARITY = 15

    # Convert events to minutes
    busy_times = []
    for event in events:
        start = time_to_minutes(event["start"])
        end = time_to_minutes(event["end"])
        if start >= end:
            raise ValueError(f"Event start time must be before end time: {event}")
        # Clip events to working hours
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

    for start, end in merged:
        while current_time + meeting_duration <= start:
            available_slots.append(minutes_to_time(current_time))
            current_time += GRANULARITY
        current_time = max(current_time, end)

    # After last event, using the same working hours on every day.
    while current_time + meeting_duration <= WORK_END:
        available_slots.append(minutes_to_time(current_time))
        current_time += GRANULARITY

    if date_obj == now.date():
        # A minute-aligned start is already past if any part of that minute elapsed.
        earliest_start = now.hour * 60 + now.minute
        if now.second or now.microsecond:
            earliest_start += 1
        available_slots = [
            slot for slot in available_slots
            if time_to_minutes(slot) >= earliest_start
        ]

    return available_slots
