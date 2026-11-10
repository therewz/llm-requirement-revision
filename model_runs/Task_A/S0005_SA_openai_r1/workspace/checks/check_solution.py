import importlib.util
from pathlib import Path
import random

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def event(start, end):
    return {"start": start, "end": end}


empty = suggest_slots([], 30, "Monday")
assert len(empty) == 31
assert empty[0] == "09:00" and empty[-1] == "16:30"
assert "12:00" in empty and "12:45" in empty
assert suggest_slots([], 30, "Friday") == empty
assert suggest_slots([], 30, "2026-02-13") == empty
assert suggest_slots([], 480, "Monday") == ["09:00"]
for duration in (0, -1, 481, 1.5):
    assert suggest_slots([], duration, "Monday") == []
assert suggest_slots([event("09:00", "17:00")], 1, "Monday") == []

slots = suggest_slots([event("10:00", "11:00")], 30, "Monday")
assert "09:30" in slots and "11:00" in slots
assert "09:45" not in slots and "10:45" not in slots
assert suggest_slots([event("08:00", "09:00"), event("17:00", "18:00")], 30, "Monday") == empty
assert suggest_slots([event("08:00", "09:30"), event("16:30", "18:00")], 30, "Monday") == [s for s in empty if "09:30" <= s <= "16:00"]
assert suggest_slots([event("10:00", "10:00"), event("12:00", "11:00")], 30, "Monday") == empty
assert suggest_slots([event("09:00", "12:00"), event("12:00", "17:00")], 15, "Monday") == []

# Compare with direct interval checks for unsorted, overlapping and non-grid events.
rng = random.Random(0)
for _ in range(200):
    intervals = []
    for _ in range(rng.randrange(15)):
        start = rng.randrange(360, 1140)
        intervals.append((start, start + rng.randrange(180)))
    events = [event(solution._to_hhmm(s), solution._to_hhmm(e)) for s, e in intervals]
    original = [dict(ev) for ev in events]
    duration = rng.randrange(1, 500)
    expected = [
        solution._to_hhmm(start)
        for start in range(540, 1020 - duration + 1, 15)
        if not any(s < e and start < e and start + duration > s for s, e in intervals)
    ]
    assert suggest_slots(events, duration, "Friday") == expected
    assert events == original

print("All checks passed.")
