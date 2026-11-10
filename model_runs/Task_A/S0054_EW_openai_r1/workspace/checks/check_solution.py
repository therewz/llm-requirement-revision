import importlib.util
from pathlib import Path
import random

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)

friday = "2026-07-17"
monday = "2026-07-20"
slots = solution.suggest_slots([], 30, friday)
assert len(slots) == 451
assert slots[0] == "09:00" and slots[-1] == "16:30"
assert "15:01" in slots and "12:00" in slots and "09:01" in slots
assert slots == solution.suggest_slots([], 30, monday)
assert solution.suggest_slots([], 480, friday) == ["09:00"]
assert solution.suggest_slots([], 481, friday) == []
assert solution.suggest_slots([], 1441, friday) == []
assert solution.suggest_slots([], 17, friday)[-1] == "16:43"

# Immediate adjacency to an event is allowed, but crossing it is not.
events = [{"start": "10:00", "end": "10:30"}]
slots = solution.suggest_slots(events, 30, friday)
assert "09:30" in slots and "10:30" in slots
assert "09:31" not in slots and "10:29" not in slots
assert solution.suggest_slots(
    [{"start": "09:00", "end": "12:00"},
     {"start": "12:00", "end": "17:00"}], 1, friday
) == []

# Check sorted, overlapping, nested, back-to-back, and out-of-hours events
# against a direct half-open-interval overlap oracle.
rng = random.Random(54)
for _ in range(300):
    intervals = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        intervals.append((start, end))
    events = [
        {"start": solution.minutes_to_time(start),
         "end": solution.minutes_to_time(end)}
        for start, end in intervals
    ]
    original = [dict(event) for event in events]
    duration = rng.choice([1, 7, 17, 30, 45, 60, 120, 480, 481, 1500])
    expected = [
        solution.minutes_to_time(start)
        for start in range(540, 1020 - duration + 1)
        if all(start + duration <= begin or start >= end
               for begin, end in intervals)
    ]
    assert solution.suggest_slots(events, duration, friday) == expected
    assert events == original

for duration in [0, -1, 1.5, "30", True]:
    try:
        solution.suggest_slots([], duration, friday)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Accepted invalid duration: {duration!r}")

for event in [
    {}, {"start": "09:00"},
    {"start": "25:00", "end": "26:00"},
    {"start": "10:00", "end": "10:00"},
    {"start": "11:00", "end": "10:00"},
]:
    try:
        solution.suggest_slots([event], 30, friday)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Accepted invalid event: {event!r}")

try:
    solution.suggest_slots([], 30, "not a date")
except ValueError:
    pass
else:
    raise AssertionError("Accepted an invalid date")

print("All slot checks passed, including 300 randomized comparisons.")
