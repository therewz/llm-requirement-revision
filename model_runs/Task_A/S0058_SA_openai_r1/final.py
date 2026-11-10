from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    if day not in ("M", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
        raise ValueError("Invalid day abbreviation")
    if day in ("Sat", "Sun"):
        return []

    def to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
            if not (0 <= h < 24 and 0 <= m < 60):
                raise ValueError
            return h * 60 + m
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Invalid time format") from None

    def to_str(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    # Use the explicitly specified 09:00-12:00 working window. This also
    # excludes lunch and ensures every meeting finishes before 17:00.
    work_start, work_end = 9 * 60, 12 * 60

    working_events = []
    for event in events:
        start = to_minutes(event["start"])
        end = to_minutes(event["end"])
        if start >= end:
            raise ValueError("Invalid event interval")
        # Events wholly outside working hours must not introduce a buffer.
        if start < work_end and end > work_start:
            working_events.append((max(start, work_start), min(end, work_end)))

    working_events.sort()
    merged = []
    for start, end in working_events:
        if not merged or merged[-1][1] < start:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    valid = []
    for start in range(work_start, work_end - meeting_duration + 1, 15):
        end = start + meeting_duration
        # A meeting may end at an event's start, but must start at least
        # 15 minutes after an event's end.
        if all(end <= event_start or start >= event_end + 15
               for event_start, event_end in merged):
            valid.append(to_str(start))

    return valid
