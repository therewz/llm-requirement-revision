import importlib.util
from pathlib import Path
import random

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def rejects(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


empty = s.suggest_slots([], 30, "Mo")
assert len(empty) == 26
assert empty[0] == "09:00" and empty[-1] == "16:30"
assert "11:30" in empty and "13:00" in empty
assert "11:45" not in empty and "12:00" not in empty
assert "17:00" not in empty
assert s.suggest_slots([], 30, "Fr") == empty
assert s.suggest_slots([], 30, "Sa") == empty
assert s.suggest_slots([], 5, "Tu")
assert s.suggest_slots([], 241, "We") == []
assert s.suggest_slots([{"start": "09:00", "end": "17:00"}], 30, "Th") == []

slots = s.suggest_slots([{"start": "10:00", "end": "11:00"}], 30, "Mo")
assert "09:15" in slots and "09:30" not in slots
assert "11:00" not in slots and "11:15" in slots
assert slots == s.suggest_slots([{"begin": "10:00", "end": "11:00"}], 30, "Mo")
assert s.suggest_slots([{"start": "12:15", "end": "12:30"}], 30, "Mo") == empty

for value in [0, -1, 1.5, "30", None, True]:
    rejects(lambda: s.suggest_slots([], value, "Mo"))
for day in ["2026-01-01", "Monday", "xx", None, ""]:
    rejects(lambda: s.suggest_slots([], 30, day))
for time in ["4pm", "04:00 PM", "24:00", "09:60", "9:30", "09:3", None, 930]:
    rejects(lambda: s.to_minutes(time))
for events in [None, {}, [None], [{}], [{"start": "10:00", "end": "09:00"}]]:
    rejects(lambda: s.suggest_slots(events, 30, "Mo"))

# Randomized safety checks cover overlaps, unordered events, and events outside work.
rng = random.Random(7)
for _ in range(500):
    intervals = []
    for _ in range(rng.randrange(10)):
        a = rng.randrange(1439)
        b = rng.randrange(a + 1, 1440)
        intervals.append((a, b))
    events = [{"start": s.to_time_str(a), "end": s.to_time_str(b)} for a, b in intervals]
    duration = rng.randrange(1, 300)
    slots = s.suggest_slots(events, duration, "Fr")
    assert slots == sorted(set(slots))
    for slot in slots:
        a = s.to_minutes(slot)
        b = a + duration
        assert 540 <= a < b <= 1020
        assert b <= 720 or a >= 780
        assert all(b + 15 <= c or a >= d + 15 for c, d in intervals)

print("All checks passed")
