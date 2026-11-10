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
assert "12:00" in suggest([], 30, "Mon")
assert "16:30" in suggest([], 30, "Fri")
assert suggest([], 30, "Sat") == []
assert suggest([], 30, "Sun") == []
assert suggest([], 30, "2026-07-20") == suggest([], 30, "Mon")
assert suggest([], 30, "2026-07-19") == []
for duration in (0, -1, 1440, 5000, 1.5, "30", None, True, False):
    assert suggest([], duration, "Mon") == []
for duration in (1, 30, 480, 1000):
    assert suggest([{"start": "09:00", "end": "17:00"}], duration, "Mon") == []
assert suggest([
    {"start": "08:00", "end": "12:03"},
    {"start": "12:04", "end": "18:00"},
], 1, "Mon") == ["12:03"]
malformed = [None, [], 1, "bad", {}, {"start": "25:00", "end": "26:00"},
             {"start": "09:99", "end": "12:00"},
             {"start": "11:00", "end": "10:00"}]
assert suggest(malformed, 30, "Mon") == suggest([], 30, "Mon")
assert suggest(None, 30, "Mon") == suggest([], 30, "Mon")
for day in ("Foo", "Funday", "Monday", 12):
    try:
        suggest([], 30, day)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Invalid day accepted: {day}")

real_date = datetime.date
class Monday(real_date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 20)

with patch.object(solution.datetime, "date", Monday):
    for day in (None, "", "today", "2026-02-30", "2026-13-01"):
        assert suggest([], 30, day) == suggest([], 30, "Mon")

class Sunday(real_date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 19)

with patch.object(solution.datetime, "date", Sunday):
    assert suggest([], 30, None) == []

rng = random.Random(47)
for _ in range(300):
    intervals = []
    for _ in range(rng.randrange(10)):
        start, end = sorted(rng.sample(range(1440), 2))
        intervals.append((start, end))
    events = [{"start": solution.minutes_to_time(a), "end": solution.minutes_to_time(b)}
              for a, b in intervals]
    duration = rng.randrange(1, 600)
    expected = [solution.minutes_to_time(start)
                for start in range(540, 1020 - duration + 1)
                if all(start + duration <= a or start >= b for a, b in intervals)]
    assert suggest(events, duration, "Fri") == expected
print("All checks passed (including 300 randomized schedules).")
