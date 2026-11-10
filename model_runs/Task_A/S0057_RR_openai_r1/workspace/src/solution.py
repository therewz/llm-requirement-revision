from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Suggest start times in 15-minute steps within each available gap.

    Working hours are 09:00-17:00 on weekdays. Friday meetings may start
    no later than 15:00, but may finish after that time. Weekends have no
    available slots. Returned times are alternatives for a single meeting.
    """
    # -----------------------------
    # Validation
    # -----------------------------
    weekdays = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    if not isinstance(day, str) or len(day) != 3 or day.lower() not in weekdays:
        raise ValueError("Day must be a three-letter weekday name")
    day = day.lower()

    if isinstance(meeting_duration, bool) or not isinstance(meeting_duration, int) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be a positive integer")

    if day in {"sat", "sun"}:
        return []

    # -----------------------------
    # Helpers
    # -----------------------------
    def to_minutes(t: str) -> int:
        try:
            h, m = map(int, t.split(":"))
            return h * 60 + m
        except (ValueError, AttributeError, TypeError):
            raise ValueError("Invalid time format")

    def to_str(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    # -----------------------------
    # Constants
    # -----------------------------
    WORK_START = 9 * 60
    WORK_END = 17 * 60
    latest_start = 15 * 60 if day == "fri" else WORK_END

    # -----------------------------
    # Normalize events
    # -----------------------------
    intervals = []
    for e in events:
        start = to_minutes(e["start"])
        end = to_minutes(e["end"])

        if start >= end:
            raise ValueError("Invalid event interval")

        # Clip to working hours
        start = max(start, WORK_START)
        end = min(end, WORK_END)

        if start < end:
            intervals.append((start, end))

    # -----------------------------
    # Merge intervals
    # -----------------------------
    intervals.sort()
    merged = []
    for s, e in intervals:
        if not merged or merged[-1][1] < s:
            merged.append([s, e])
        else:
            merged[-1][1] = max(merged[-1][1], e)

    # -----------------------------
    # Find free gaps
    # -----------------------------
    free = []
    prev = WORK_START
    for s, e in merged:
        if prev < s:
            free.append((prev, s))
        prev = max(prev, e)

    if prev < WORK_END:
        free.append((prev, WORK_END))

    # -----------------------------
    # Generate slots (15-min increments)
    # -----------------------------
    result = []
    for start, end in free:
        current = start
        while current + meeting_duration <= end and current <= latest_start:
            result.append(to_str(current))
            current += 15

    return result
