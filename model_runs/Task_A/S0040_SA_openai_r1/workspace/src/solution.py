from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return every valid HH:MM start for a meeting during 09:00–17:00.

    Events belong to the supplied day and use 'start' and 'end' HH:MM
    values. All days use the same business hours. Meetings may begin as
    soon as an event ends and may end exactly when another event begins.
    """
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    BUSINESS_START = "09:00"
    BUSINESS_END = "17:00"

    def time_to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
        except Exception:
            raise ValueError(f"Invalid time format: {t}")
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError(f"Invalid time value: {t}")
        return h * 60 + m

    def minutes_to_time(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    day_start = time_to_minutes(BUSINESS_START)
    day_end = time_to_minutes(BUSINESS_END)

    normalized_events = []
    for e in events:
        try:
            start = time_to_minutes(e['start'])
            end = time_to_minutes(e['end'])
        except KeyError:
            raise ValueError("Event must have 'start' and 'end'")
        if start >= end:
            raise ValueError(f"Event start >= end: {e}")
        normalized_events.append((start, end))

    free_slots = []
    previous_end = day_start
    for start, end in sorted(normalized_events):
        # Ignore time outside business hours before finding gaps.
        event_start = max(start, day_start)
        event_end = min(end, day_end)
        if event_start >= event_end:
            continue

        if event_start - previous_end >= meeting_duration:
            free_slots.append((previous_end, event_start))
        previous_end = max(previous_end, event_end)

    if day_end - previous_end >= meeting_duration:
        free_slots.append((previous_end, day_end))

    # HH:MM has minute precision; do not impose a coarser scheduling grid.
    available_starts = []
    for start, end in free_slots:
        for slot_start in range(start, end - meeting_duration + 1):
            available_starts.append(minutes_to_time(slot_start))

    return available_starts
