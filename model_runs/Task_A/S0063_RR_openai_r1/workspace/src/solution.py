from datetime import datetime, timedelta
from typing import List, Dict

def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str, friday_override=False) -> List[str]:
    """Return available 15-minute-grid starts within 09:00-17:00.

    Lunch is 12:00-13:00. Friday starts are always limited to 15:00;
    friday_override is retained for call compatibility but cannot bypass this.
    """
    # -----------------------------
    # Input validation
    # -----------------------------
    if meeting_duration < 0:
        raise ValueError("Meeting duration cannot be negative")
    if meeting_duration == 0:
        return []

    try:
        day_dt = datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Invalid date format, must be YYYY-MM-DD")

    weekday = day_dt.weekday()  # Monday=0 ... Sunday=6

    # -----------------------------
    # Working hours
    # -----------------------------
    work_start = day_dt.replace(hour=9, minute=0)
    work_end = day_dt.replace(hour=17, minute=0)
    friday_cutoff = day_dt.replace(hour=15, minute=0)

    # -----------------------------
    # Build busy intervals
    # -----------------------------
    busy_intervals = []

    for e in events:
        try:
            start_dt = datetime.strptime(e["start"], "%H:%M").replace(
                year=day_dt.year, month=day_dt.month, day=day_dt.day
            )
            end_dt = datetime.strptime(e["end"], "%H:%M").replace(
                year=day_dt.year, month=day_dt.month, day=day_dt.day
            )
        except Exception:
            raise ValueError("Invalid time format in events")

        if start_dt >= end_dt:
            raise ValueError("Event start time must be before end time")

        busy_intervals.append((start_dt, end_dt))

    # Lunch break (12:00-13:00)
    lunch_start = day_dt.replace(hour=12, minute=0)
    lunch_end = day_dt.replace(hour=13, minute=0)
    busy_intervals.append((lunch_start, lunch_end))

    # -----------------------------
    # Clip intervals to working hours
    # -----------------------------
    clipped = []
    for start, end in busy_intervals:
        if end <= work_start or start >= work_end:
            continue
        clipped.append((max(start, work_start), min(end, work_end)))

    # -----------------------------
    # Merge overlapping intervals
    # -----------------------------
    clipped.sort()
    merged = []
    for start, end in clipped:
        if not merged:
            merged.append((start, end))
        else:
            last_start, last_end = merged[-1]
            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))

    # -----------------------------
    # Generate candidate slots (15-min grid)
    # -----------------------------
    slots = []
    current = work_start
    step = timedelta(minutes=15)
    meeting_td = timedelta(minutes=meeting_duration)

    while current + meeting_td <= work_end:
        # Friday cutoff: cannot start after 15:00, even with an override
        if weekday == 4 and current > friday_cutoff:
            break

        end_time = current + meeting_td

        # Check overlap with busy intervals
        conflict = any(current < b_end and end_time > b_start for b_start, b_end in merged)

        if not conflict:
            slots.append(current.strftime("%H:%M"))

        current += step

    return slots