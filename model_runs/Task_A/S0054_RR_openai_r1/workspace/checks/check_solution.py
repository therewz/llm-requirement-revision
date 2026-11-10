import importlib.util
import random
from pathlib import Path

spec = importlib.util.spec_from_file_location("solution", Path(__file__).resolve().parents[1] / "src" / "solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest = solution.suggest_slots
fmt = solution.minutes_to_time

monday = "2026-02-02"
friday = "2026-02-06"
assert suggest([], 30, monday) == [fmt(t) for t in range(540, 991)]
assert suggest([], 7, monday) == [fmt(t) for t in range(540, 1014)]
assert "12:00" in suggest([], 60, monday)
assert suggest([], 120, friday)[-1] == "15:00"
assert suggest([], 1, friday)[-1] == "15:00"
assert suggest([], 121, friday)[-1] == "14:59"
assert suggest([], 480, friday) == ["09:00"]
assert suggest([], 481, monday) == []
assert suggest([], 1500, friday) == []
assert suggest([{"start": "08:00", "end": "18:00"}], 1, friday) == []

events = [{"start": "10:00", "end": "11:00"}, {"start": "09:30", "end": "10:00"}]
original = [dict(event) for event in events]
slots = suggest(events, 30, monday)
assert slots[0] == "09:00"
assert slots[1] == "11:00"
assert events == original
assert "09:01" not in slots
assert "15:00" not in suggest([{"start": "15:30", "end": "16:00"}], 60, friday)
assert suggest([{"start": "00:00", "end": "09:00"}, {"start": "17:00", "end": "23:59"}], 480, monday) == ["09:00"]

for duration in [0, -1, 1.5, True, "30", None]:
    try:
        suggest([], duration, monday)
    except ValueError:
        pass
    else:
        raise AssertionError(("invalid duration accepted", duration))
for event in [{"start": "10:00"}, {"start": "10:00", "end": "10:00"}, {"start": "25:00", "end": "26:00"}, {"start": "11:00", "end": "10:00"}]:
    try:
        suggest([event], 30, monday)
    except ValueError:
        pass
    else:
        raise AssertionError(("invalid event accepted", event))
try:
    suggest([], 30, "2026-02-30")
except ValueError:
    pass
else:
    raise AssertionError("invalid date accepted")

rng = random.Random(54)
for _ in range(500):
    intervals = []
    for _ in range(rng.randrange(15)):
        start = rng.randrange(1439)
        intervals.append((start, rng.randrange(start + 1, 1440)))
    rng.shuffle(intervals)
    events = [{"start": fmt(start), "end": fmt(end)} for start, end in intervals]
    duration = rng.randrange(1, 600)
    day = rng.choice([monday, friday])
    expected = [fmt(t) for t in range(540, 1020 - duration + 1)
                if (day != friday or t <= 900)
                and all(t + duration <= start or t >= end for start, end in intervals)]
    assert suggest(events, duration, day) == expected

print("All deterministic checks and 500 randomized comparisons passed.")
