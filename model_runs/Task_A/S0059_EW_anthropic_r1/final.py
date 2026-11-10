from typing import List, Dict


def suggest_slots(events: List[Dict[str, str]], meeting_duration: int, day: str) -> List[str]:
    # ---------- Step 0: Validate inputs ----------
    if meeting_duration <= 0:
        raise ValueError("Meeting duration must be positive")

    # `day` is informational only and does not affect scheduling.

    # 15-min granularity for candidate start times
    GRANULARITY = 15

    # Working hours
    work_start = 9 * 60
    work_end = 17 * 60

    # ---------- Step 1: Convert and validate events ----------
    parsed = []
    for e in events:
        try:
            start_h, start_m = map(int, e['start'].split(':'))
            end_h, end_m = map(int, e['end'].split(':'))
        except Exception:
            raise ValueError("Invalid time format in events")
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        if start >= end:
            raise ValueError("Event start time must be before end time")
        parsed.append((start, end))

    # ---------- Step 2: Sort and merge overlapping events ----------
    parsed.sort()
    merged = []
    for start, end in parsed:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    # ---------- Step 3: Compute free intervals within working hours ----------
    free_intervals = []
    prev_end = work_start
    for s, e in merged:
        if s > prev_end:
            free_intervals.append((prev_end, min(s, work_end)))
        prev_end = max(prev_end, e)
        if prev_end >= work_end:
            break
    if prev_end < work_end:
        free_intervals.append((prev_end, work_end))

    # ---------- Step 4: Generate slots ----------
    slots = []
    for s, e in free_intervals:
        # Align s to next 15-min boundary
        s = ((s + GRANULARITY - 1) // GRANULARITY) * GRANULARITY
        while s + meeting_duration <= e:
            slots.append(f"{s // 60:02d}:{s % 60:02d}")
            s += GRANULARITY

    return sorted(slots)
