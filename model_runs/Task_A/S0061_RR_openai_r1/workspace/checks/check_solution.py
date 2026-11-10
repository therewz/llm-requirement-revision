import copy
import importlib.util
import random
from datetime import datetime
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)

MONDAY = "2026-02-02"
FRIDAY = "2026-02-06"


def oracle(events, duration, day):
    busy = [(720, 780)] + [
        (solution.to_minutes(e["start"]), solution.to_minutes(e["end"]))
        for e in events
    ]
    return [
        solution.to_time_str(t)
        for t in range(540, 1020, 15)
        if t + duration <= 1020
        and (datetime.strptime(day, "%Y-%m-%d").weekday() != 4 or t <= 900)
        and all(t + duration <= start or t >= end for start, end in busy)
    ]


friday_slots = solution.suggest_slots([], 60, FRIDAY)
assert "15:00" in friday_slots
assert "15:15" not in friday_slots
assert "15:00" in solution.suggest_slots([], 120, FRIDAY)
assert "15:00" not in solution.suggest_slots([], 121, FRIDAY)
assert "16:00" in solution.suggest_slots([], 60, MONDAY)
assert "11:30" in solution.suggest_slots([], 30, MONDAY)
assert "11:45" not in solution.suggest_slots([], 30, MONDAY)
assert "13:00" in solution.suggest_slots([], 30, MONDAY)
assert "10:00" in solution.suggest_slots(
    [{"start": "09:00", "end": "10:00"}], 30, MONDAY
)
assert solution.suggest_slots(
    [{"start": "09:05", "end": "17:00"}], 5, MONDAY
) == ["09:00"]
assert solution.suggest_slots(
    [{"start": "09:00", "end": "16:55"}], 5, MONDAY
) == []  # Remaining time does not contain an aligned start.
assert solution.suggest_slots([], 241, MONDAY) == []
assert solution.suggest_slots(
    [{"start": "00:00", "end": "23:59"}], 1, FRIDAY
) == []
for duration in (0, -1):
    try:
        solution.suggest_slots([], duration, MONDAY)
    except ValueError:
        pass
    else:
        raise AssertionError("Nonpositive duration should be rejected")

rng = random.Random(42)
for case in range(500):
    events = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        events.append({"start": solution.to_time_str(start), "end": solution.to_time_str(end)})
    rng.shuffle(events)
    original = copy.deepcopy(events)
    for duration in (1, 5, 15, 20, 30, 45, 59, 60, 120, 180, 240, 241, 600):
        for day in (MONDAY, FRIDAY):
            actual = solution.suggest_slots(events, duration, day)
            expected = oracle(events, duration, day)
            assert actual == expected, (events, duration, day, actual, expected)
    assert events == original

print("All boundary and randomized checks passed.")
