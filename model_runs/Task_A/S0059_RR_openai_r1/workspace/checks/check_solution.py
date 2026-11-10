import importlib.util
import random

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def fmt(minute):
    return f"{minute // 60:02d}:{minute % 60:02d}"


assert len(suggest_slots([], 1, "Monday")) == 480
assert suggest_slots([], 480, "informational label") == ["09:00"]
assert suggest_slots([], 481, "Monday") == []
assert "12:00" in suggest_slots([], 17, "Monday")
assert suggest_slots([], 30, "Friday")[-1] == "15:00"
assert suggest_slots([], 120, "2026-07-24")[-1] == "15:00"
assert suggest_slots([], 121, "Friday")[-1] == "14:59"
assert suggest_slots([], 30, "2026-07-23")[-1] == "16:30"
assert suggest_slots([{"start": "08:00", "end": "18:00"}], 1, "Monday") == []
events = [{"start": "10:00", "end": "11:00"}]
slots = suggest_slots(events, 30, "Monday")
assert "09:30" in slots and "11:00" in slots
assert "09:31" not in slots and "10:59" not in slots
try:
    suggest_slots([], 0, "Monday")
except ValueError:
    pass
else:
    raise AssertionError("Nonpositive duration accepted")

rng = random.Random(2026)
for _ in range(300):
    intervals = []
    for _ in range(rng.randrange(15)):
        start = rng.randrange(24 * 60 - 1)
        intervals.append((start, rng.randrange(start + 1, 24 * 60)))
    rng.shuffle(intervals)
    events = [{"start": fmt(s), "end": fmt(e)} for s, e in intervals]
    original = [e.copy() for e in events]
    duration = rng.randrange(1, 550)
    for day, friday in [("arbitrary label", False), ("Friday", True), ("2026-07-24", True)]:
        expected = [
            fmt(start)
            for start in range(9 * 60, 17 * 60 - duration + 1)
            if (not friday or start <= 15 * 60)
            and all(start + duration <= s or start >= e for s, e in intervals)
        ]
        assert suggest_slots(events, duration, day) == expected
        assert events == original
print("All scheduling checks passed.")
