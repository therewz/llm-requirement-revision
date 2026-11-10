from typing import List, Dict
from datetime import datetime

def time_to_minutes(t: str) -> int:
    """Convert 'HH:MM' string to minutes since midnight."""
    try:
        h, m = map(int, t.split(":"))
    except Exception:
        raise ValueError(f"Invalid time format: {t}")
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"Invalid time value: {t}")
    return h * 60 + m

def minutes_to_time(m: int) -> str:
    """Convert minutes since midnight to 'HH:MM' string."""
    h = m // 60
    m = m % 60
    return f"{h:02d}:{m:02d}"

def _is_friday(day) -> bool:
    """Best-effort detection of Friday from the day identifier.

    Accepts an ISO date ('YYYY-MM-DD') or a weekday name ('Friday'/'Fri').
    Any other identifier is not treated as Friday.
    """
    if not isinstance(day, str):
        return False
    s = day.strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d").weekday() == 4
    except ValueError:
        pass
    return s.lower() in ("friday", "fri")

def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Suggest meeting slots respecting working hours, events, 15-min grid, and Friday cutoff."""

    # Validate meeting duration
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    is_friday = _is_friday(day)

    # Define working periods
    working_periods = [
        (time_to_minutes("09:00"), time_to_minutes("12:00")),
        (time_to_minutes("13:00"), time_to_minutes("17:00"))
    ]

    # Friday cutoff: meetings may not start after 15:00
    friday_max_start = time_to_minutes("15:00")

    # Convert events to minutes and validate
    busy_intervals = []
    for event in events:
        start = time_to_minutes(event["start"])
        end = time_to_minutes(event["end"])
        if end <= start:
            raise ValueError(f"Event end time must be after start time: {event}")
        # Only keep intervals overlapping working hours (others are ignored)
        for wp_start, wp_end in working_periods:
            if start < wp_end and end > wp_start:
                busy_intervals.append((max(start, wp_start), min(end, wp_end)))

    busy_intervals.sort()

    # Generate candidate slots on 15-min grid
    slots = []
    for wp_start, wp_end in working_periods:
        t = wp_start
        while t + meeting_duration <= wp_end:
            if is_friday and t > friday_max_start:
                break
            slots.append(t)
            t += 15

    # Filter out slots that conflict with existing events
    valid_slots = []
    for slot_start in slots:
        slot_end = slot_start + meeting_duration
        conflict = False
        for ev_start, ev_end in busy_intervals:
            # overlap check
            if slot_start < ev_end and slot_end > ev_start:
                conflict = True
                break
            # For >=30 min meetings, cannot start exactly at an event end
            if meeting_duration >= 30 and slot_start == ev_end:
                conflict = True
                break
        if not conflict:
            valid_slots.append(minutes_to_time(slot_start))

    return valid_slots
