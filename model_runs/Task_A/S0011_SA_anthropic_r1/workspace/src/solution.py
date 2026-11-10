"""
Meeting slot suggestion exercise.

`suggest_slots` returns a list of valid meeting start times on a given day,
respecting working hours (09:00-17:00) and not conflicting with existing events.
"""


from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    if meeting_duration <= 0:
        return []

    def to_minutes(hhmm: str) -> int:
        h, m = hhmm.strip().split(":")
        return int(h) * 60 + int(m)

    def to_hhmm(x: int) -> str:
        return f"{x // 60:02d}:{x % 60:02d}"

    WORK_START = to_minutes("09:00")
    WORK_END = to_minutes("17:00")
    STEP = 15

    # Parse events and clip to working hours; ignore events fully outside.
    busy = []
    for e in events:
        if "start" not in e or "end" not in e:
            continue
        s = to_minutes(e["start"])
        t = to_minutes(e["end"])
        if t <= s:
            continue
        s = max(s, WORK_START)
        t = min(t, WORK_END)
        if t > s:
            busy.append((s, t))

    # Merge overlapping/touching busy intervals
    busy.sort()
    merged = []
    for s, t in busy:
        if not merged or s > merged[-1][1]:
            merged.append([s, t])
        else:
            merged[-1][1] = max(merged[-1][1], t)

    latest_start = WORK_END - meeting_duration
    if latest_start < WORK_START:
        return []

    res: List[str] = []
    start = WORK_START
    i = 0
    while start <= latest_start:
        end = start + meeting_duration

        while i < len(merged) and merged[i][1] <= start:
            i += 1

        # First busy interval ending after start; if it doesn't overlap,
        # no later one can either.
        if not (i < len(merged) and merged[i][0] < end):
            res.append(to_hhmm(start))

        start += STEP

    return res
