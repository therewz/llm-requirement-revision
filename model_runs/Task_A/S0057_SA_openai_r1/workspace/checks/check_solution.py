import importlib.util
import random

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suggest_slots = module.suggest_slots


def time(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def minutes(value):
    h, m = map(int, value.split(":"))
    return 60 * h + m


assert suggest_slots([], 60, "Mon") == [time(m) for m in range(540, 1020, 60)]
assert suggest_slots([], 60, "Fri")[-1] == "16:00"
assert "12:00" in suggest_slots([], 60, "Tue")
assert suggest_slots([], 1, "Wed") == [time(m) for m in range(540, 1020)]
assert suggest_slots([], 17, "Thu") == [time(m) for m in range(540, 1004, 17)]
assert suggest_slots([], 480, "Mon") == ["09:00"]
assert suggest_slots([], 481, "Mon") == []
assert suggest_slots([], 30, "SAT") == []
assert suggest_slots([], 30, "Sun") == []
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 15, "Mon") == []
assert suggest_slots([{"start": "09:00", "end": "09:23"}], 60, "Mon")[0] == "09:23"
assert suggest_slots([{"start": "10:00", "end": "16:00"}], 60, "Mon") == ["09:00", "16:00"]

for day in ("Monday", "2025-01-01", "", None, "123"):
    try:
        suggest_slots([], 30, day)
    except ValueError:
        pass
    else:
        raise AssertionError(day)
for duration in (0, -1, 2.5, "30"):
    try:
        suggest_slots([], duration, "Mon")
    except ValueError:
        pass
    else:
        raise AssertionError(duration)

# Compare with a minute-by-minute earliest-fit oracle, including events that
# overlap, duplicate each other, or extend beyond working hours.
rng = random.Random(42)
for _ in range(500):
    busy = []
    for _ in range(rng.randrange(15)):
        start = rng.randrange(1440)
        end = rng.randrange(start + 1, 1441)
        busy.append((start, end))
    events = [{"start": time(s), "end": time(e)} for s, e in busy]
    before = [dict(event) for event in events]
    duration = rng.randrange(1, 510)
    expected = []
    current = 540
    while current + duration <= 1020:
        if any(current < e and s < current + duration for s, e in busy):
            current += 1
        else:
            expected.append(time(current))
            current += duration
    actual = suggest_slots(events, duration, "Mon")
    assert actual == expected, (busy, duration, actual, expected)
    assert events == before
    assert len(actual) == len(set(actual))
    assert all(minutes(a) + duration <= minutes(b) for a, b in zip(actual, actual[1:]))

print("All checks passed (including 500 randomized schedules).")
