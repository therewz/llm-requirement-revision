import importlib.util
import random

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def stamp(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# Friday has the same availability as other weekdays, including after 15:00.
expected = [stamp(t) for a, b in [(540, 720), (780, 1020)]
            for t in range(a, b - 30 + 1, 15)]
for day in ["M", "Mon", "Tue", "Wed", "Thu", "Fri"]:
    assert suggest_slots([], 30, day) == expected
assert "15:00" in expected and "16:30" in expected
assert "13:00" in expected
for day in ["Sat", "Sun"]:
    assert suggest_slots([], 30, day) == []

# Durations need not be multiples of 30 or even 15 minutes.
for duration in [1, 15, 20, 31, 180, 181, 240, 241, 1000]:
    expected = [stamp(t) for a, b in [(540, 720), (780, 1020)]
                for t in range(a, b - duration + 1, 15)]
    assert suggest_slots([], duration, "Mon") == expected

outside = [{"start": "07:00", "end": "09:00"},
           {"start": "12:00", "end": "13:00"},
           {"start": "17:00", "end": "19:00"}]
assert suggest_slots(outside, 30, "Fri") == suggest_slots([], 30, "Fri")

events = [{"start": "10:00", "end": "10:30"}]
slots = suggest_slots(events, 30, "Mon")
assert "09:30" in slots and "09:45" not in slots
assert "10:30" not in slots and "10:45" in slots
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 15, "Wed") == []

# Real ends determine the buffer, including events spanning lunch.
assert "13:00" not in suggest_slots(
    [{"start": "11:00", "end": "13:00"}], 15, "Tue")
assert "13:15" in suggest_slots(
    [{"start": "11:00", "end": "13:00"}], 15, "Tue")
assert "13:00" in suggest_slots(
    [{"start": "11:00", "end": "12:00"}] + outside, 15, "Tue")

# Compare against a minute-by-minute reference and check order independence.
rng = random.Random(58)
work = set(range(540, 720)) | set(range(780, 1020))
for _ in range(100):
    intervals = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(1440)
        end = rng.randrange(start + 1, 1441)
        # The input format permits hours only up to 23.
        end = min(end, 1439)
        if start < end:
            intervals.append((start, end))
    duration = rng.randrange(1, 300)
    blocked = set()
    for start, end in intervals:
        if work.intersection(range(start, end)):
            blocked.update(range(start, end + 15))
    expected = []
    for start in range(0, 1440, 15):
        meeting = set(range(start, start + duration))
        if meeting <= work and not meeting.intersection(blocked):
            expected.append(stamp(start))
    events = [{"start": stamp(a), "end": stamp(b)} for a, b in intervals]
    original = [dict(event) for event in events]
    assert suggest_slots(events, duration, "Fri") == expected
    assert events == original
    rng.shuffle(events)
    assert suggest_slots(events, duration, "Mon") == expected

print("All checks passed")
