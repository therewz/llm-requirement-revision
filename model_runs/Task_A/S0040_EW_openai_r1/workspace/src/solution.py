from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # Validate meeting duration (in minutes).
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    # Business hours apply equally to every day.
    BUSINESS_START = "09:00"
    BUSINESS_END = "17:00"

    # Helper to convert time string to minutes.
    def time_to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
        except Exception:
            raise ValueError(f"Invalid time format: {t}")
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError(f"Invalid time value: {t}")
        return h * 60 + m

    # Helper to convert minutes to time string.
    def minutes_to_time(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    day_start = time_to_minutes(BUSINESS_START)
    day_end = time_to_minutes(BUSINESS_END)

    # Validate and normalize events without modifying the input.
    normalized_events = []
    for e in events:
        try:
            start = time_to_minutes(e['start'])
            end = time_to_minutes(e['end'])
        except KeyError:
            raise ValueError("Event must have 'start' and 'end'")
        if start >= end:
            raise ValueError(f"Event start >= end: {e}")
        normalized_events.append({'start': start, 'end': end})

    sorted_events = sorted(normalized_events, key=lambda x: x['start'])

    # Find free intervals inside business hours. Meetings may touch events.
    free_slots = []
    previous_end = day_start
    for event in sorted_events:
        event_start = max(event['start'], day_start)
        event_end = min(event['end'], day_end)
        if event_start >= event_end or event_end <= previous_end:
            continue

        if event_start - previous_end >= meeting_duration:
            free_slots.append((previous_end, event_start))
        previous_end = max(previous_end, event_end)

    if day_end - previous_end >= meeting_duration:
        free_slots.append((previous_end, day_end))

    # HH:MM inputs have minute precision, so return every valid minute.
    available_starts = []
    for start, end in free_slots:
        for slot_start in range(start, end - meeting_duration + 1):
            available_starts.append(minutes_to_time(slot_start))

    return available_starts
