from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # -----------------------------
    # Validation
    # -----------------------------
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    if day not in {"M", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}:
        raise ValueError("Invalid day")
    if day in {"Sat", "Sun"}:
        return []

    # -----------------------------
    # Helpers
    # -----------------------------
    def to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
            if not (0 <= h < 24 and 0 <= m < 60):
                raise ValueError
            return h * 60 + m
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Invalid time format")

    def to_str(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    # -----------------------------
    # Working blocks (excluding lunch)
    # -----------------------------
    blocks = [(9 * 60, 12 * 60), (13 * 60, 17 * 60)]

    # Ignore events wholly outside working hours. Keep actual event ends
    # so the buffer is measured from the event, not a clipped boundary.
    working_events = []
    for event in events:
        start = to_minutes(event["start"])
        end = to_minutes(event["end"])
        if start >= end:
            raise ValueError("Invalid event interval")
        if any(start < we and end > ws for ws, we in blocks):
            working_events.append((start, end))

    # -----------------------------
    # Generate and validate candidates in chronological order
    # -----------------------------
    valid = []
    for ws, we in blocks:
        for start in range(ws, we - meeting_duration + 1, 15):
            end = start + meeting_duration
            if any(
                start < event_end + 15 and end > event_start
                for event_start, event_end in working_events
            ):
                continue
            valid.append(to_str(start))

    return valid
