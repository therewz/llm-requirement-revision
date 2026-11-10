from typing import List, Dict

WORK_START = 9 * 60
WORK_END = 17 * 60
LUNCH_START = 12 * 60
LUNCH_END = 13 * 60
INTERVAL = 15  # start times align to 15-minute increments


def to_minutes(t: str) -> int:
    try:
        h, m = map(int, t.strip().split(":"))
    except Exception:
        raise ValueError(f"Invalid time format: {t}")
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"Invalid time value: {t}")
    return h * 60 + m


def to_time_str(m: int) -> str:
    h, mi = divmod(m, 60)
    return f"{h:02d}:{mi:02d}"


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    # Busy intervals from events (input order is irrelevant) plus lunch.
    busy = [(LUNCH_START, LUNCH_END)]
    for e in events:
        busy.append((to_minutes(e["start"]), to_minutes(e["end"])))

    slots = []
    t = WORK_START
    while t + meeting_duration <= WORK_END:
        end = t + meeting_duration
        if all(end <= s or t >= e for s, e in busy):
            slots.append(to_time_str(t))
        t += INTERVAL

    return slots
