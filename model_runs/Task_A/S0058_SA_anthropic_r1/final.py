from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # -----------------------------
    # Validation
    # -----------------------------
    if not isinstance(meeting_duration, int) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be a positive integer")

    day_key = str(day).strip().lower()
    day_map = {
        "m": 0, "mon": 0,
        "tue": 1, "wed": 2, "thu": 3, "fri": 4,
        "sat": 5, "sun": 6,
    }
    if day_key not in day_map:
        raise ValueError("Invalid day")
    if day_map[day_key] >= 5:  # weekends are ignored
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

    # Working blocks (lunch 12-13 excluded)
    blocks = [(9 * 60, 12 * 60), (13 * 60, 17 * 60)]

    # Events that do not intersect working hours have no effect
    relevant = [
        (s, e_) for s, e_ in parsed
        if any(s < we and e_ > ws for ws, we in blocks)
    ]

    # -----------------------------
    # Generate and validate candidates
    # -----------------------------
    valid = []
    for ws, we in blocks:
        start = ws
        while start + meeting_duration <= we:
            end = start + meeting_duration
            ok = True
            for es, ee in relevant:
                if start < ee and end > es:      # overlap
                    ok = False
                    break
                if ee <= start < ee + 15:        # 15-min buffer after event
                    ok = False
                    break
            if ok:
                valid.append(start)
            start += 15

    return [to_str(t) for t in sorted(valid)]
