import datetime
import importlib.util
import random
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest = solution.suggest_slots

assert len(suggest([], 30, "Mon")) == 451
assert suggest([], 480, "Mon") == ["09:00"]
assert suggest([], 481, "Mon") == []
assert "12:00" in suggest([], 30, "Mon")
for duration in (0, -1, 1440, 2000, 1.5, "30", None, True, False):
    assert suggest([], duration, "Mon") == []
for day in ("Sat", "Sun", "2025-01-04", "2025-01-05"):
    assert suggest([], 1, day) == []
assert suggest([], 1, "Fri")[-1] == "15:00"
assert suggest([], 120, "2025-01-03")[-1] == "15:00"
assert suggest([], 121, "Fri")[-1] == "14:59"
assert suggest([{"start": "09:00", "end": "17:00"}], 1, "Mon") == []
assert suggest([
    {"start": "09:00", "end": "12:07"},
    {"start": "12:08", "end": "17:00"},
], 1, "Mon") == ["12:07"]
assert suggest([
    {"start": "09:00", "end": "15:01"},
], 1, "Fri") == []
malformed = [None, [], ["09:00", "10:00"], {}, {"start": "bad"},
             {"start": "09:99", "end": "12:00"},
             {"start": "10:00", "end": "09:00"},
             {"start": None, "end": "12:00"}]
assert suggest(malformed, 30, "Mon") == suggest([], 30, "Mon")
assert suggest(None, 30, "Mon") == suggest([], 30, "Mon")
try:
    suggest([], 30, "Bad")
except ValueError:
    pass
else:
    raise AssertionError("Invalid weekday was not marked invalid")

class Monday(datetime.date):
    @classmethod
    def today(cls):
        return cls(2025, 1, 6)

with patch.object(solution.datetime, "date", Monday):
    for day in (None, "", "2025-99-99", "not a date"):
        assert suggest([], 30, day) == suggest([], 30, "Mon")

rng = random.Random(42)
for _ in range(300):
    events = []
    intervals = []
    for _ in range(rng.randrange(15)):
        a, b = sorted(rng.sample(range(1440), 2))
        events.append({"start": solution.minutes_to_time(a),
                       "end": solution.minutes_to_time(b)})
        intervals.append((a, b))
    duration = rng.randrange(1, 600)
    for day in ("Mon", "Fri"):
        expected = [solution.minutes_to_time(t)
                    for t in range(540, 1020 - duration + 1)
                    if (day != "Fri" or t <= 900)
                    and all(t + duration <= a or t >= b for a, b in intervals)]
        assert suggest(events, duration, day) == expected
print("All checks passed (including 600 randomized comparisons).")
