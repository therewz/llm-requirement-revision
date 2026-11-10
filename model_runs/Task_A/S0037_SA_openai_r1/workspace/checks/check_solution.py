import copy
import importlib.util
import random
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def minutes(value):
    h, m = map(int, value.split(":"))
    return h * 60 + m


def time(value):
    return f"{value // 60:02d}:{value % 60:02d}"


def reference(events, duration):
    if duration <= 0:
        return []
    busy = [(720, 780)] + [
        (minutes(e["start"]), min(1440, minutes(e["end"]) + 15))
        for e in events
    ]
    return [
        time(s)
        for s in range(540, 1020 - duration + 1, 15)
        if not 720 <= s <= 780
        and all(s + duration <= a or s >= b for a, b in busy)
    ]


empty = suggest_slots([], 30, "Mon")
assert empty == reference([], 30)
assert "11:30" in empty
assert "11:45" not in empty
assert "12:00" not in empty
assert "13:00" not in empty
assert "13:15" in empty
assert "16:30" in empty
assert "16:45" not in empty
assert suggest_slots([], 30, "2026-06-05") == empty  # Friday
assert suggest_slots([], 30, "Fri") == empty
assert suggest_slots([], 600, "Mon") == []
assert suggest_slots([], 0, "Mon") == []
assert suggest_slots([{"start": "00:00", "end": "23:59"}], 15, "Mon") == []

buffered = suggest_slots([{"start": "09:00", "end": "09:30"}], 15, "Mon")
assert "09:30" not in buffered
assert "09:45" in buffered
# A 15-minute gap cannot hold a 30-minute meeting.
events = [{"start": "09:00", "end": "10:00"},
          {"start": "10:30", "end": "11:00"}]
assert "10:15" not in suggest_slots(events, 30, "Mon")
# Buffer is not applied again after merging overlapping buffered intervals.
events = [{"start": "09:00", "end": "10:00"},
          {"start": "09:30", "end": "10:30"}]
assert "10:45" in suggest_slots(events, 15, "Mon")

rng = random.Random(37)
for _ in range(500):
    events = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(96) * 15
        end = rng.randrange(start // 15 + 1, 97) * 15
        events.append({"start": time(start), "end": time(end)})
    duration = rng.choice([1, 10, 15, 20, 30, 45, 60, 90, 120, 240, 480, 600])
    original = copy.deepcopy(events)
    actual = suggest_slots(events, duration, "2026-06-05")
    assert actual == reference(events, duration), (events, duration, actual)
    assert events == original
    assert all(minutes(slot) % 15 == 0 for slot in actual)

print("All checks passed (including 500 randomized schedules).")
