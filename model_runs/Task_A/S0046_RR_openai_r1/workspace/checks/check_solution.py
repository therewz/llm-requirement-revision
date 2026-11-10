import importlib.util
from datetime import datetime
from pathlib import Path
import random

spec = importlib.util.spec_from_file_location("solution", Path(__file__).resolve().parents[1] / "src" / "solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)

class FrozenDatetime(datetime):
    current = datetime(2030, 1, 7, 10, 7, 30)  # Monday

    @classmethod
    def now(cls):
        return cls.current

solution.datetime = FrozenDatetime
slots = solution.suggest_slots
minutes = solution.time_to_minutes

# Empty calendars, positive sub-15-minute durations, and end-of-day limits.
assert slots([], 60, "2030-01-08") == [solution.minutes_to_time(t) for t in range(540, 961, 15)]
assert slots([], 1, "2030-01-08")[-1] == "16:45"
assert slots([], 480, "2030-01-08") == ["09:00"]
assert slots([], 481, "2030-01-08") == []

# Friday's limit is a start-time limit, not an end-time limit.
assert slots([], 60, "2030-01-11")[-1] == "15:00"
assert slots([], 120, "2030-01-11")[-1] == "15:00"
assert slots([], 135, "2030-01-11")[-1] == "14:45"
assert slots([], 30, "Friday")[-1] == "15:00"

# Past dates and elapsed start times must be excluded.
assert slots([], 30, "2030-01-06") == []
assert slots([], 30, "2030-01-07")[0] == "10:15"
assert slots([], 30, "Monday") == slots([], 30, "2030-01-07")
assert slots([], 30, "Tuesday")[0] == "09:00"
FrozenDatetime.current = datetime(2030, 1, 7, 10, 15)
assert slots([], 30, "Monday")[0] == "10:15"
FrozenDatetime.current = datetime(2030, 1, 7, 10, 15, 0, 1)
assert slots([], 30, "Monday")[0] == "10:30"
FrozenDatetime.current = datetime(2030, 1, 7, 17)
assert slots([], 30, "Monday") == []

# Adjacent boundaries do not conflict; overlapping events merge.
events = [{"start": "10:00", "end": "11:00"}, {"start": "10:30", "end": "12:00"}]
result = slots(events, 60, "2030-01-08")
assert "09:00" in result and "12:00" in result
assert "09:15" not in result and "11:45" not in result
assert slots([{"start": "08:00", "end": "18:00"}], 1, "2030-01-08") == []

for invalid in (0, -1, 1.5, True):
    try:
        slots([], invalid, "2030-01-08")
    except ValueError:
        pass
    else:
        raise AssertionError(f"Accepted invalid duration {invalid}")

# Validate invariants across irregular, unordered and overlapping events.
rng = random.Random(46)
for _ in range(200):
    busy = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(480, 1080)
        end = rng.randrange(start + 1, 1141)
        busy.append((start, end))
    duration = rng.randrange(1, 600)
    day = rng.choice(["2030-01-08", "2030-01-11"])
    events = [{"start": solution.minutes_to_time(s), "end": solution.minutes_to_time(e)} for s, e in busy]
    result = slots(events, duration, day)
    assert result == sorted(set(result))
    for slot in result:
        start = minutes(slot)
        assert start >= 540 and start + duration <= 1020
        assert day != "2030-01-11" or start <= 900
        assert all(start + duration <= s or start >= e for s, e in busy)

print("All checks passed.")
