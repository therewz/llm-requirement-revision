import copy
import importlib.util
import random
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def hhmm(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


slots = suggest_slots([], 30, "Monday")
assert slots == [hhmm(t) for t in range(540, 991)]
assert "12:00" in slots and "09:01" in slots
for day in ("Fri", "Friday", "2026-07-24", "Saturday", ""):
    assert suggest_slots([], 30, day) == slots
assert "16:30" in suggest_slots([], 30, "Friday")
assert suggest_slots([], 480, "Monday") == ["09:00"]
for duration in (0, -1, 481):
    assert suggest_slots([], duration, "Monday") == []
assert suggest_slots([{"start": "08:00", "end": "18:00"}], 1, "Mon") == []
assert suggest_slots([
    {"start": "09:00", "end": "12:07"},
    {"start": "12:37", "end": "17:00"},
], 30, "Fri") == ["12:07"]
assert suggest_slots([
    {"start": "07:00", "end": "09:00"},
    {"start": "17:00", "end": "18:00"},
], 30, "Mon") == slots

rng = random.Random(17)
for _ in range(300):
    intervals = [(rng.randrange(420, 1141), rng.randrange(420, 1141))
                 for _ in range(rng.randrange(12))]
    events = [{"start": hhmm(s), "end": hhmm(e)} for s, e in intervals]
    rng.shuffle(events)
    original = copy.deepcopy(events)
    duration = rng.randrange(1, 501)
    expected = [hhmm(t) for t in range(540, 1020 - duration + 1)
                if all(e <= s or not (t < e and s < t + duration)
                       for s, e in intervals)]
    assert suggest_slots(events, duration, "Friday") == expected
    assert events == original

print("All checks passed (boundaries, restrictions removed, and 300 randomized cases).")
