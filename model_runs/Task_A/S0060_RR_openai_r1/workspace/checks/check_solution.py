import datetime
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from solution import minutes_to_time, suggest_slots, time_to_minutes


MONDAY = "2026-07-13"
FRIDAY = "2026-07-17"

slots = suggest_slots([], 1, MONDAY)
assert slots == [minutes_to_time(m) for m in range(8 * 60, 11 * 60)]
assert suggest_slots([], 1, FRIDAY) == slots
assert suggest_slots([], 9, MONDAY) == ["08:00"]
assert suggest_slots([], 10, MONDAY) == []
assert suggest_slots([], 8, MONDAY)[-1] == "09:00"
assert suggest_slots([], 7, MONDAY)[-1] == "10:00"

assert suggest_slots([{"start": "08:00", "end": "17:00"}], 1, MONDAY) == []
assert suggest_slots(["08:00-17:00"], 1, MONDAY) == []
assert suggest_slots(["09:00-10:00"], 1, MONDAY) == ["08:00"] + [
    minutes_to_time(m) for m in range(10 * 60, 11 * 60)
]
assert suggest_slots(["08:00-09:00"], 1, MONDAY)[0] == "09:00"
assert suggest_slots(["08:01-08:02"], 1, MONDAY)[0] == "08:02"
assert suggest_slots(["00:00-01:00", "18:00-19:00"], 1, MONDAY) == slots
assert suggest_slots([], 4, MONDAY) == slots  # No imposed lunch exclusion.
assert suggest_slots(["08:00-09:00", "08:30-10:00"], 1, MONDAY) == (
    suggest_slots(["08:00-10:00"], 1, MONDAY)
)

for invalid in (0, -1, 1.5, "1", True):
    try:
        suggest_slots([], invalid, MONDAY)
    except ValueError:
        pass
    else:
        raise AssertionError(("Accepted invalid duration", invalid))
for args in (((), 1, MONDAY), ([], 1, "2026-02-30"), (["24:00-24:30"], 1, MONDAY)):
    try:
        suggest_slots(*args)
    except ValueError:
        pass
    else:
        raise AssertionError(("Accepted invalid arguments", args))

rng = random.Random(24)
for _ in range(200):
    duration = rng.randint(1, 10)
    intervals = []
    for _ in range(rng.randint(0, 8)):
        start = rng.randrange(0, 1439)
        end = rng.randrange(start + 1, 1440)
        intervals.append((start, end))
    events = [
        {"start": minutes_to_time(start), "end": minutes_to_time(end)}
        for start, end in intervals
    ]
    day = rng.choice([MONDAY, FRIDAY])
    expected = []
    for start in range(24 * 60):
        end = start + duration * 60
        if not (8 * 60 <= start < 11 * 60 and end <= 17 * 60):
            continue
        if datetime.date.fromisoformat(day).weekday() == 4 and start > 15 * 60:
            continue
        if any(start < event_end and end > event_start for event_start, event_end in intervals):
            continue
        expected.append(minutes_to_time(start))
    assert suggest_slots(events, duration, day) == expected
    assert [time_to_minutes(t) for t in expected] == sorted(set(map(time_to_minutes, expected)))

print("All checks passed (including 200 randomized comparisons).")
