import copy
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from solution import suggest_slots, _to_hhmm, _to_minutes


assert suggest_slots([], 60, "Mon") == [
    "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"
]
friday = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00"]
for day in ("Fri", " friday ", "FRI", "2026-06-05"):
    assert suggest_slots([], 60, day) == friday
assert suggest_slots([], 120, "Friday") == ["09:00", "13:00", "15:00"]
assert suggest_slots([], 45, "Fri") == [
    "09:00", "09:45", "10:30", "11:15", "13:00", "13:45", "14:30"
]
assert suggest_slots([], 90, "Mon") == ["09:00", "10:30", "13:00", "14:30"]
for day in ("Sat", "Sunday", "2026-06-06", "2026-06-07", "holiday"):
    assert suggest_slots([], 30, day) == []
for duration in (0, -1, 481, 1000):
    try:
        suggest_slots([], duration, "Mon")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid duration accepted")
assert suggest_slots([], 480, "Mon") == []
assert suggest_slots([], 241, "Mon") == []
assert suggest_slots([], 240, "Fri") == ["13:00"]

# No cooldown or quarter-hour rounding; use the earliest free start.
events = [{"start": "09:00", "end": "09:07"}]
assert suggest_slots(events, 60, "Mon") == [
    "09:07", "10:07", "13:00", "14:00", "15:00", "16:00"
]
assert suggest_slots([{"start": "09:15", "end": "09:45"}], 30, "Mon")[:4] == [
    "09:45", "10:15", "10:45", "11:15"
]
assert suggest_slots([{"start": "08:00", "end": "09:00"}], 60, "Mon")[0] == "09:00"
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, "Mon") == []
assert suggest_slots([{"start": "15:00", "end": "17:00"}], 60, "Fri") == friday[:-1]
assert suggest_slots([{"start": "09:00", "end": "15:00"}], 120, "Fri") == ["15:00"]
assert suggest_slots([{"start": "09:00", "end": "15:01"}], 30, "Fri") == []

# Day/date filtering, including distinct dates sharing a weekday.
for event_day in ("Tue", "Tuesday", "2026-06-02"):
    assert suggest_slots([{"start": "09:00", "end": "17:00", "day": event_day}], 60, "Mon") == suggest_slots([], 60, "Mon")
assert suggest_slots([{"start": "09:00", "end": "17:00", "date": "2026-06-12"}], 60, "2026-06-05") == friday
assert suggest_slots([{"start": "09:00", "end": "17:00", "date": "2026-06-05"}], 60, "2026-06-05") == []
assert suggest_slots([{"start": "09:00", "end": "17:00", "day": "friday"}], 60, "2026-06-05") == []
assert suggest_slots([{"day": "Mon", "is_holiday": True}], 30, "Monday") == []
assert suggest_slots([{"date": "2026-06-05", "holiday": True}], 30, "2026-06-05") == []
assert suggest_slots([{"day": "Tue", "is_holiday": True}], 60, "Fri") == friday

invalid = [None, {}, {"start": "bad", "end": "10:00"},
           {"start": "10:00", "end": "09:00"},
           {"start": "10:00", "end": "10:00"},
           {"start": "24:00", "end": "25:00"},
           {"start": None, "end": "10:00"}]
assert suggest_slots(invalid, 60, "Fri") == friday

# Randomized oracle: scan minute by minute, taking the earliest possible
# start and then skipping exactly one meeting duration after accepting it.
rng = random.Random(53)
for _ in range(500):
    events = []
    intervals = [(720, 780)]
    for _ in range(rng.randrange(12)):
        start = rng.randrange(0, 1439)
        end = rng.randrange(start + 1, 1440)
        events.append({"start": _to_hhmm(start), "end": _to_hhmm(end)})
        intervals.append((start, end))
    rng.shuffle(events)
    original = copy.deepcopy(events)
    duration = rng.randrange(1, 481)
    day = rng.choice(["Mon", "Fri"])
    expected = []
    start = 540
    while start + duration <= 1020 and (day != "Fri" or start <= 900):
        if all(start + duration <= s or start >= e for s, e in intervals):
            expected.append(_to_hhmm(start))
            start += duration
        else:
            start += 1
    actual = suggest_slots(events, duration, day)
    assert actual == expected, (events, duration, day, actual, expected)
    assert events == original
    assert actual == sorted(actual)
    assert all(_to_minutes(b) - _to_minutes(a) >= duration for a, b in zip(actual, actual[1:]))

print("All targeted checks and 500 randomized cases passed.")
