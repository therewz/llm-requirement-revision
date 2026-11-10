from typing import List, Dict


def time_to_minutes(t: str) -> int:
    """Convert HH:MM string to minutes since midnight."""
    try:
        h, m = map(int, t.split(":"))
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError
        return h * 60 + m
    except Exception:
        raise ValueError(f"Invalid time format: {t}")


def minutes_to_time(m: int) -> str:
    """Convert minutes since midnight to HH:MM string."""
    h = m // 60
    m = m % 60
    return f"{h:02d}:{m:02d}"


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return ascending 'HH:MM' start times for a meeting of meeting_duration
    minutes within working hours (09:00-17:00), not overlapping any event or
    the lunch break (12:00-13:00). `day` is accepted (day name or date) but
    does not alter the working-hours rules."""
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    LUNCH_START = 12 * 60
    LUNCH_END = 13 * 60
    STEP = 15

    busy = []
    for e in events:
        if "start" not in e or "end" not in e:
            raise ValueError("Event must have 'start' and 'end'")
        s = time_to_minutes(e["start"])
        t = time_to_minutes(e["end"])
        if s >= t:
            raise ValueError(f"Invalid event interval: {e}")
        # Events outside working hours are clipped away / ignored
        start = max(s, WORK_START)
        end = min(t, WORK_END)
        if start < end:
            busy.append((start, end))

    busy.append((LUNCH_START, LUNCH_END))

    slots = []
    t = WORK_START
    while t + meeting_duration <= WORK_END:
        slot_end = t + meeting_duration
        if all(slot_end <= s or t >= e for s, e in busy):
            slots.append(minutes_to_time(t))
        t += STEP

    return slots
