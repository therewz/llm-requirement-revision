from typing import List, Dict
from datetime import datetime


_DAY_MAP = {
    "m": 0, "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # -----------------------------
    # Validation
    # -----------------------------
    if not isinstance(meeting_duration, int) or isinstance(meeting_duration, bool) or meeting_duration <= 0:
        raise ValueError("Meeting duration must be a positive integer")

    key = str(day).strip().lower()
    if key in _DAY_MAP:
        weekday = _DAY_MAP[key]
    else:
        # Backward compatibility: accept an ISO date
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

    DAY_START = 9 * 60
    DAY_END = 17 * 60
    blocks = [(9 * 60, 12 * 60), (13 * 60, 17 * 60)]  # lunch 12-13 excluded
    BUFFER = 15
    FRIDAY_LAST_START = 15 * 60  # Fridays: no start after 15:00
    is_friday = weekday == 4

    # -----------------------------
    # Parse events (order-independent); clip to working hours
    # -----------------------------
    working_events = []
    for e in events:
        s = to_minutes(e["start"])
        en = to_minutes(e["end"])
        if s >= en:
            raise ValueError("Invalid event interval")
        cs, ce = max(s, DAY_START), min(en, DAY_END)
        if cs < ce:  # events fully outside working hours are ignored
            working_events.append((cs, ce))

    # -----------------------------
    # Generate and validate candidates
    # -----------------------------
    valid = []
    for ws, we in blocks:
        t = ws
        while t + meeting_duration <= we:
            if is_friday and t > FRIDAY_LAST_START:
                break
            end = t + meeting_duration
            ok = True
            for es, ee in working_events:
                if t < ee and end > es:  # overlap
                    ok = False
                    break
                if ee <= t < ee + BUFFER:  # buffer after event
                    ok = False
                    break
            if ok:
                valid.append(t)
            t += 15

    return [to_str(t) for t in sorted(valid)]
