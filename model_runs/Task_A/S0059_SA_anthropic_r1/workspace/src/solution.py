from typing import List, Dict


def _to_minutes(value: str) -> int:
    try:
        h, m = value.strip().split(':')
        h, m = int(h), int(m)
    except Exception:
        raise ValueError("Invalid time format: %r" % (value,))
    if not (0 <= h <= 24 and 0 <= m < 60):
        raise ValueError("Invalid time format: %r" % (value,))
    return h * 60 + m


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str = "") -> List[str]:
    # The day parameter is informational only and does not affect scheduling.
    if not isinstance(meeting_duration, int) or isinstance(meeting_duration, bool) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be a positive integer (minutes)")

    GRANULARITY = 15
    work_start = 9 * 60
    work_end = 17 * 60

    # Parse events (may be unsorted / empty)
    intervals = []
    for e in events or []:
        start = _to_minutes(e['start'])
        end = _to_minutes(e['end'])
        if start >= end:
            raise ValueError("Event start time must be before end time")
        intervals.append((start, end))
    intervals.sort()

    slots = []
    s = work_start
    while s + meeting_duration <= work_end:
        e = s + meeting_duration
        # Overlap if s < ev_end and ev_start < e (touching boundaries allowed)
        if not any(s < ev_end and ev_start < e for ev_start, ev_end in intervals):
            slots.append(f"{s // 60:02d}:{s % 60:02d}")
        s += GRANULARITY
    return slots
