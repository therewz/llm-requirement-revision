import importlib.util
import random
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots
to_time = solution.minutes_to_time

# Friday follows the same rules as other days, including late afternoon.
friday = suggest_slots([], 30, "Friday")
assert friday == suggest_slots([], 30, "Monday")
assert friday == suggest_slots([], 30, "2026-02-06")
assert "15:01" in friday and "16:30" in friday
assert "16:31" not in friday
assert "09:00" in friday and "11:30" in friday and "13:00" in friday
assert "11:31" not in friday and "12:00" not in friday

# No arbitrary duration, start-grid, or buffer restrictions.
slots = suggest_slots([{"start": "10:03", "end": "10:37"}], 17, "Friday")
assert "09:46" in slots  # Ends exactly at an event's start.
assert "09:47" not in slots
assert "10:36" not in slots
assert "10:37" in slots  # Starts exactly at an event's end.
assert "11:43" in slots and "11:44" not in slots
assert "16:43" in slots and "16:44" not in slots

outside = [{"start": "07:00", "end": "09:00"},
           {"start": "17:00", "end": "20:00"}]
assert suggest_slots(outside, 30, "Friday") == friday
assert suggest_slots([{"start": "08:00", "end": "18:00"}], 30, "Friday") == []
assert suggest_slots([], 241, "Friday") == []
assert suggest_slots([], 240, "Friday") == ["13:00"]

# Compare against a simple minute-occupancy oracle for unordered/overlapping events.
rng = random.Random(56)
for _ in range(100):
    events = []
    occupied = set(range(720, 780))
    for _ in range(rng.randrange(12)):
        start, end = sorted(rng.sample(range(1440), 2))
        events.append({"start": to_time(start), "end": to_time(end)})
        occupied.update(range(start, end))
    duration = rng.randrange(1, 300)
    expected = [to_time(t) for t in range(540, 1020 - duration + 1)
                if occupied.isdisjoint(range(t, t + duration))]
    assert suggest_slots(events, duration, "Friday") == expected
    rng.shuffle(events)
    assert suggest_slots(events, duration, "Tuesday") == expected

for duration in (0, -1, 1.5, True):
    try:
        suggest_slots([], duration, "Friday")
    except ValueError:
        pass
    else:
        raise AssertionError("Accepted invalid duration")

for event in ({"start": "10:00", "end": "10:00"},
              {"start": "10:00", "end": "09:00"},
              {"start": "25:00", "end": "26:00"},
              {"start": "09:00"}):
    try:
        suggest_slots([event], 30, "Friday")
    except ValueError:
        pass
    else:
        raise AssertionError("Accepted invalid event")

print("All scheduling checks passed.")
