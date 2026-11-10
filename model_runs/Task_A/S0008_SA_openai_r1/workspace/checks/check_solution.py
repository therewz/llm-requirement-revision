import importlib.util
import random

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def fmt(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


assert suggest_slots([], 480, "Mon") == ["09:00"]
assert suggest_slots([], 481, "Mon") == []
assert suggest_slots([], 0, "Mon") == []
assert suggest_slots([], -1, "Mon") == []
free = suggest_slots([], 30, "Fri")
assert free == [fmt(t) for t in range(540, 991)]
assert "12:00" in free and "16:30" in free and "09:01" in free
assert suggest_slots([], 30, "2026-01-02") == free
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 1, "Mon") == []
assert suggest_slots([
    {"start": "08:00", "end": "10:00"},
    {"start": "10:30", "end": "18:00"},
], 30, "Mon") == ["10:00"]
assert suggest_slots([
    {"start": "08:00", "end": "09:00"},
    {"start": "17:00", "end": "18:00"},
], 480, "Mon") == ["09:00"]

rng = random.Random(42)
for _ in range(200):
    intervals = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(0, 1440)
        end = rng.randrange(start, 1440)
        intervals.append((start, end))
    events = [{"start": fmt(s), "end": fmt(e)} for s, e in intervals]
    rng.shuffle(events)
    original = [ev.copy() for ev in events]
    duration = rng.randrange(1, 501)
    expected = [fmt(t) for t in range(540, 1020 - duration + 1)
                if all(not (t < e and t + duration > s)
                       for s, e in intervals if s < e)]
    assert suggest_slots(events, duration, "Fri") == expected
    assert events == original

print("All checks passed.")
