from typing import List, Dict, Optional


def suggest_slots(
    events: List[Dict[str, str]],
    meeting_duration: int,
    day: Optional[str] = None
) -> List[str]:
    """
    Suggest possible meeting start times for a day.

    Args:
        events: List of dicts with keys {"start": "HH:MM", "end": "HH:MM"}
        meeting_duration: Desired meeting length in minutes
        day: Unused; accepted for call-signature compatibility.

    Returns:
        List of valid start times as "HH:MM" sorted ascending (empty if none).

    Notes:
        - Working hours are 09:00 to 17:00; the meeting must fit inside them.
        - Candidate start times are on a 15-minute grid.
        - A meeting may start exactly when an event ends and may end exactly
          when an event starts (back-to-back is allowed); overlap is not.
    """
    if meeting_duration <= 0:
        return []

    work_start = 9 * 60
    work_end = 17 * 60
    if meeting_duration > work_end - work_start:
        return []

    def to_minutes(t: str) -> int:
        h, m = t.strip().split(":")
        return int(h) * 60 + int(m)

    busy = []
    for ev in events:
        s = to_minutes(ev["start"])
        e = to_minutes(ev["end"])
        if s < e:
            busy.append((s, e))

    slots = []
    for start in range(work_start, work_end - meeting_duration + 1, 15):
        end = start + meeting_duration
        if any(start < e and s < end for s, e in busy):
            continue
        slots.append(f"{start // 60:02d}:{start % 60:02d}")

    return slots
