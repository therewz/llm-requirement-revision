"""Suggest conflict-free meeting start times within 09:00–17:00."""

from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    """Return valid HH:MM starts at one-minute resolution, in time order.

    Durations are in minutes. Events are for the supplied day; the same working
    hours apply regardless of its name or date. Meetings may end exactly when
    an event starts, start exactly when an event ends, or end at 17:00.
    """
    if meeting_duration <= 0:
        return []

    def to_minutes(hhmm: str) -> int:
        hhmm = hhmm.strip()
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)

    def to_hhmm(x: int) -> str:
        return f"{x//60:02d}:{x%60:02d}"

    WORK_START = to_minutes("09:00")
    WORK_END = to_minutes("17:00")

    # Clip events to working hours; ignore events fully outside.
    busy = []
    for e in events:
        if "start" not in e or "end" not in e:
            continue
        s = to_minutes(e["start"])
        t = to_minutes(e["end"])
        if t <= s:
            continue

        if t <= WORK_START or s >= WORK_END:
            continue

        s = max(s, WORK_START)
        t = min(t, WORK_END)
        if t > s:
            busy.append((s, t))

    # Merge overlapping/touching busy intervals.
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

        overlaps = False
        if i < len(merged):
            bs, bt = merged[i]
            if start < bt and bs < end:
                overlaps = True

        if not overlaps:
            res.append(to_hhmm(start))

        start += 1

    return res
