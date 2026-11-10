import datetime
import importlib.util
import random
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest = solution.suggest_slots

assert suggest([], 30, "Mon")[0] == "09:00"
assert suggest([], 30, "Mon")[-1] == "16:30"
assert "15:01" in suggest([], 30, "Fri")
assert "16:59" in suggest([], 1, "Fri")
assert "12:30" in suggest([], 30, "Mon")
assert suggest([], 480, "Fri") == ["09:00"]
assert suggest([], 481, "Mon") == []
for duration in (None, "30", 30.0, True, False, 0, -1, 1440, 2000):
    assert suggest([], duration, "Mon") == []
for day in ("Sat", "Sun", "2025-01-04", "2025-01-05"):
    assert suggest([], 30, day) == []
assert suggest([], 30, "2025-01-03") == suggest([], 30, "Fri")
try:
    suggest([], 30, "Bad")
except ValueError:
    pass
else:
    raise AssertionError("Invalid weekday was not marked invalid")

class FixedDateTime(datetime.datetime):
    @classmethod
    def today(cls):
        return cls(2025, 1, 6)

with patch.object(solution.datetime, "datetime", FixedDateTime):
    for day in (None, "", "today", "2025-02-30", "not-a-date"):
        assert suggest([], 30, day) == suggest([], 30, "Mon")

full = [{"start": "09:00", "end": "17:00"}]
for duration in (1, 30, 480, 1439):
    assert suggest(full, duration, "Mon") == []
assert suggest([
    {"start": "09:00", "end": "12:07"},
    {"start": "12:08", "end": "17:00"},
], 1, "Fri") == ["12:07"]
malformed = [None, [], ["09:00", "17:00"], {},
             {"start": "oops", "end": "17:00"},
             {"start": "09:60", "end": "17:00"},
             {"start": "24:00", "end": "25:00"},
             {"start": "15:00", "end": "09:00"}]
assert suggest(malformed, 30, "Mon") == suggest([], 30, "Mon")
for malformed_collection in (None, {}, "events", 42):
    assert suggest(malformed_collection, 30, "Mon") == suggest([], 30, "Mon")

rng = random.Random(47)
for _ in range(250):
    intervals = []
    events = []
    for _ in range(rng.randrange(15)):
        start = rng.randrange(1440)
        end = rng.randrange(start + 1, 1441)
        # 24:00 is not an HH:MM time; stop at 23:59 instead.
        end = min(end, 1439)
        if end <= start:
            continue
        intervals.append((start, end))
        events.append({"start": solution.minutes_to_time(start),
                       "end": solution.minutes_to_time(end)})
    duration = rng.randint(1, 600)
    expected = [solution.minutes_to_time(start)
                for start in range(540, 1020 - duration + 1)
                if all(start + duration <= a or start >= b
                       for a, b in intervals)]
    assert suggest(events, duration, "Fri") == expected

print("All scheduling checks passed (including 250 randomized schedules).")
