import importlib.util
from pathlib import Path
import random

spec = importlib.util.spec_from_file_location("solution", Path(__file__).resolve().parents[1] / "src" / "solution.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suggest_slots = module.suggest_slots


def time_string(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


assert suggest_slots([], 30, "Mon") == [time_string(t) for t in range(540, 991)]
assert "12:00" in suggest_slots([], 60, "Mon")
assert "09:01" in suggest_slots([], 30, "Mon")
assert suggest_slots([], 480, "Mon") == ["09:00"]
assert suggest_slots([], 481, "Mon") == []
assert suggest_slots([], 0, "Mon") == []
assert suggest_slots([], -1, "Mon") == []
assert suggest_slots([{"start": "08:00", "end": "18:00"}], 1, "Mon") == []

adjacent = suggest_slots([{"start": "10:00", "end": "11:00"}], 30, "Mon")
assert "09:30" in adjacent
assert "09:31" not in adjacent
assert "10:59" not in adjacent
assert "11:00" in adjacent

for friday in ("Fri", "2026-06-12"):
    assert suggest_slots([], 30, friday)[-1] == "15:00"
    assert suggest_slots([], 120, friday)[-1] == "15:00"
    assert suggest_slots([], 121, friday)[-1] == "14:59"
    assert suggest_slots([{"start": "09:00", "end": "15:01"}], 30, friday) == []
assert suggest_slots([], 30, "2026-06-11")[-1] == "16:30"

rng = random.Random(42)
for _ in range(300):
    intervals = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(420, 1150)
        end = start + rng.randrange(1, 180)
        intervals.append((start, end))
    events = [{"start": time_string(s), "end": time_string(e)} for s, e in intervals]
    original = [dict(event) for event in events]
    duration = rng.randrange(1, 500)
    day = rng.choice(["Mon", "Fri"])
    expected = [
        time_string(t)
        for t in range(540, 1020 - duration + 1)
        if (day != "Fri" or t <= 900)
        and all(t + duration <= s or t >= e for s, e in intervals)
    ]
    assert suggest_slots(events, duration, day) == expected
    assert events == original

print("All checks passed (including 300 randomized comparisons).")
