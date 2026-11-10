from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # -----------------------------
    # Validation
    # -----------------------------
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    if day not in ("M", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
        raise ValueError("Invalid day")
    if day in ("Sat", "Sun"):
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
        except (ValueError, AttributeError):
            raise ValueError("Invalid time format")

    def to_str(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    # Meetings must fit entirely within one working block, excluding lunch.
    blocks = [(9 * 60, 12 * 60), (13 * 60, 17 * 60)]

    # -----------------------------
    # Parse events
    # -----------------------------
    parsed = []
    for event in events:
        start = to_minutes(event["start"])
        end = to_minutes(event["end"])
        if start >= end:
            raise ValueError("Invalid event interval")
        # Ignore wholly off-hours events before merging so that they cannot
        # extend a working event's buffer. Keep actual endpoints for the rest.
        if any(start < we and end > ws for ws, we in blocks):
            parsed.append((start, end))

    parsed.sort()

    # -----------------------------
    # Merge overlapping events
    # -----------------------------
    merged = []
    for start, end in parsed:
        if not merged or merged[-1][1] < start:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    # -----------------------------
    # Generate and validate candidate start times
    # -----------------------------
    valid = []
    for ws, we in blocks:
        start = ws
        while start + meeting_duration <= we:
            # A Friday meeting may start at 15:00, but not later.
            if day == "Fri" and start > 15 * 60:
                break
            end = start + meeting_duration
            if all(end <= es or start >= ee + 15 for es, ee in merged):
                valid.append(start)
            start += 15

    return [to_str(t) for t in valid]
