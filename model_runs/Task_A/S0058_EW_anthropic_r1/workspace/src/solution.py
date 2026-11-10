from typing import List, Dict
from datetime import datetime


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # -----------------------------
    # Validation
    # -----------------------------
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    # Day: 3-letter abbreviations (plus "M" for Monday)
    day_map = {
        "m": 0, "mon": 0, "tue": 1, "wed": 2, "thu": 3,
        "fri": 4, "sat": 5, "sun": 6,
    }
    key = day.strip().lower() if isinstance(day, str) else None
    if key in day_map:
        weekday = day_map[key]
    else:
        # Backward compatibility: ISO date string
        try:
            weekday = datetime.strptime(day, "%Y-%m-%d").weekday()
        except Exception:
            raise ValueError("Invalid day")

    if weekday >= 5:  # weekend
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
        except Exception:
            raise ValueError("Invalid time format")

    def to_str(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    # -----------------------------
    # Parse events
    # -----------------------------
    parsed = []
    for e in events:
        s = to_minutes(e["start"])
        e_ = to_minutes(e["end"])
        if s >= e_:
            raise ValueError("Invalid event interval")
        parsed.append((s, e_))

    parsed.sort()

    # -----------------------------
    # Merge overlapping events
    # -----------------------------
    merged = []
    for s, e_ in parsed:
        if not merged or merged[-1][1] < s:
            merged.append([s, e_])
        else:
            merged[-1][1] = max(merged[-1][1], e_)
    merged = [(s, e_) for s, e_ in merged]

    # -----------------------------
    # Working blocks (lunch 12-13 excluded)
    # -----------------------------
    blocks = [(9 * 60, 12 * 60), (13 * 60, 17 * 60)]

    # -----------------------------
    # Filter events into working hours
    # -----------------------------
    working_events = []
    for s, e_ in merged:
        for ws, we in blocks:
            if not (e_ <= ws or s >= we):
                working_events.append((max(s, ws), min(e_, we)))

    # -----------------------------
    # Generate candidate start times (15-min increments)
    # -----------------------------
    candidates = []
    for ws, we in blocks:
        t = ws
        while t + meeting_duration <= we:
            candidates.append(t)
            t += 15

    # -----------------------------
    # Validate candidates
    # -----------------------------
    valid = []
    for start in candidates:
        end = start + meeting_duration
        ok = True
        for es, ee in working_events:
            # Overlap check
            if not (end <= es or start >= ee):
                ok = False
                break
            # 15-min buffer after event
            if ee <= start < ee + 15:
                ok = False
                break
        if ok:
            valid.append(start)

    return [to_str(t) for t in sorted(valid)]
