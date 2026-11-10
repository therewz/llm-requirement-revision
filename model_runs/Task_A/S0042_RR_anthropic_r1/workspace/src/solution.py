from typing import List, Dict
from datetime import datetime, timedelta

WORK_START = 9 * 60
WORK_END = 17 * 60
LUNCH_START = 12 * 60
LUNCH_END = 13 * 60
BUFFER = 15
GRANULARITY = 15
FRIDAY_CUTOFF = 15 * 60  # latest Friday start time: 15:00 in minutes

DAY_ABBREVIATIONS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

def to_minutes(t: str) -> int:
    try:
        h, m = map(int, t.split(":"))
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError
        return h * 60 + m
    except:
        raise ValueError(f"Invalid time format: {t}")

def to_time_str(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"

def merge_intervals(intervals):
    intervals.sort()
    merged = []

    for start, end in intervals:
        if not merged or merged[-1][1] < start:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    return merged

def parse_weekday(day: str) -> int:
    """Return weekday index (Monday=0 ... Friday=4) from a 2-letter
    abbreviation (e.g. 'Fr') or, for compatibility, a YYYY-MM-DD date."""
    if isinstance(day, str):
        key = day.strip().upper()
        if key in DAY_ABBREVIATIONS:
            return DAY_ABBREVIATIONS.index(key)
        try:
            return datetime.strptime(day.strip(), "%Y-%m-%d").weekday()
        except ValueError:
            pass
    raise ValueError(f"Invalid day: {day}")

def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # Validate meeting duration
    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be a positive integer")

    weekday = parse_weekday(day)  # Monday=0, Friday=4

    # Step 1: convert events + apply buffer
    blocked = []

    for e in events:
        start = to_minutes(e["start"])
        end = to_minutes(e["end"])
        if start >= end:
            raise ValueError(f"Event start must be before end: {e}")
        blocked.append((start, end + BUFFER))

    # Step 2: add lunch break
    blocked.append((LUNCH_START, LUNCH_END))

    # Step 3: merge overlaps
    blocked = merge_intervals(blocked)

    # Latest allowed start time (Fridays: no start after 15:00)
    latest_start = WORK_END - meeting_duration
    if weekday == 4:
        latest_start = min(latest_start, FRIDAY_CUTOFF)

    # Step 4: find available gaps
    slots = []
    current = WORK_START

    def add_slots(gap_start, gap_end):
        t = gap_start
        while t + meeting_duration <= gap_end and t <= latest_start:
            if t >= WORK_START:
                slots.append(to_time_str(t))
            t += GRANULARITY

    for start, end in blocked:
        if current < start:
            add_slots(current, min(start, WORK_END))
        current = max(current, end)

    # last gap after final event
    if current < WORK_END:
        add_slots(current, WORK_END)

    return sorted(slots)
