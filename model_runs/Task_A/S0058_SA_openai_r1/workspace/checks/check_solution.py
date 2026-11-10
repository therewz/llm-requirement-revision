import importlib.util
import random

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def fmt(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


assert suggest_slots([], 30, "Mon") == [fmt(t) for t in range(540, 691, 15)]
assert suggest_slots([], 17, "M") == [fmt(t) for t in range(540, 704, 15)]
assert suggest_slots([], 180, "Tue") == ["09:00"]
assert suggest_slots([], 181, "Wed") == []
assert suggest_slots([], 1, "Thu")[-1] == "11:45"
assert suggest_slots([], 30, "Fri") == suggest_slots([], 30, "Mon")
for day in ("Sat", "Sun"):
    assert suggest_slots([], 30, day) == []

outside = [
    {"start": "08:00", "end": "09:00"},
    {"start": "12:00", "end": "13:00"},
    {"start": "13:00", "end": "17:00"},
]
assert suggest_slots(outside, 30, "Mon") == suggest_slots([], 30, "Mon")
assert suggest_slots([{"start": "08:30", "end": "09:05"}], 30, "Mon")[0] == "09:30"
assert suggest_slots([{"start": "09:30", "end": "10:00"}], 30, "Mon") == [
    "09:00", "10:15", "10:30", "10:45", "11:00", "11:15", "11:30"
]
assert suggest_slots([{"start": "08:00", "end": "14:00"}], 1, "Mon") == []
assert suggest_slots([{"start": "11:45", "end": "13:00"}], 15, "Mon")[-1] == "11:30"

rng = random.Random(58)
for _ in range(300):
    intervals = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(420, 1080)
        end = rng.randrange(start + 1, 1201)
        intervals.append((start, end))
    duration = rng.randrange(1, 241)
    events = [{"start": fmt(s), "end": fmt(e)} for s, e in intervals]
    expected = []
    for start in range(540, 720, 15):
        end = start + duration
        if end > 720:
            continue
        if any(s < 720 and e > 540 and (
            (start < e and end > s) or e <= start < e + 15
        ) for s, e in intervals):
            continue
        expected.append(fmt(start))
    assert suggest_slots(events, duration, "Mon") == expected
    rng.shuffle(events)
    assert suggest_slots(events, duration, "M") == expected

print("All checks passed")
