import importlib.util
from datetime import datetime

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)


class FixedDatetime(datetime):
    current = datetime(2030, 1, 7, 10, 7, 30)  # Monday

    @classmethod
    def now(cls):
        return cls.current


solution.datetime = FixedDatetime
friday = "2030-01-11"
slots = solution.suggest_slots([], 30, friday)
assert slots == [solution.minutes_to_time(t) for t in range(540, 991, 15)]
assert "15:15" in slots and "16:30" in slots and "16:45" not in slots
assert solution.suggest_slots([], 480, friday) == ["09:00"]
assert solution.suggest_slots([], 481, friday) == []
assert solution.suggest_slots([], 5, friday)[-1] == "16:45"
assert solution.suggest_slots([], 30, "2030-01-06") == []
assert solution.suggest_slots([], 30, "2030-01-07")[0] == "10:15"
assert solution.suggest_slots([], 30, "Monday")[0] == "10:15"
assert solution.suggest_slots([], 30, "Friday") == slots

for bad in [0, -1, 1.5]:
    try:
        solution.suggest_slots([], bad, friday)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid duration accepted")

# Unsorted, overlapping, adjacent and out-of-hours events.
events = [
    {"start": "15:30", "end": "16:00"},
    {"start": "08:00", "end": "09:30"},
    {"start": "11:00", "end": "12:00"},
    {"start": "10:30", "end": "11:30"},
    {"start": "12:00", "end": "12:30"},
    {"start": "17:00", "end": "18:00"},
]
for duration in [1, 5, 15, 30, 60, 120, 480, 600]:
    actual = solution.suggest_slots(events, duration, friday)
    expected = []
    for t in range(540, 1020 - duration + 1, 15):
        if all(t + duration <= solution.time_to_minutes(e["start"])
               or t >= solution.time_to_minutes(e["end"]) for e in events):
            expected.append(solution.minutes_to_time(t))
    assert actual == expected, (duration, actual, expected)

assert solution.suggest_slots([{"start": "09:00", "end": "17:00"}], 30, friday) == []
FixedDatetime.current = datetime(2030, 1, 11, 16, 30)
assert solution.suggest_slots([], 30, friday) == ["16:30"]
FixedDatetime.current = datetime(2030, 1, 11, 16, 30, 0, 1)
assert solution.suggest_slots([], 30, friday) == []
print("All checks passed.")
