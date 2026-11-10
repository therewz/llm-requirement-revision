import importlib.util
import random
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

monday = suggest_slots([], 30, "Mon")
assert monday[0] == "09:00" and monday[-1] == "16:30"
assert "11:30" in monday and "11:45" not in monday
assert "12:00" not in monday and "12:45" not in monday
assert "13:00" in monday
friday = suggest_slots([], 30, "Fri")
assert friday[-1] == "15:00"
assert "15:15" not in friday
assert "15:00" in suggest_slots([], 120, "fri")
assert "15:00" not in suggest_slots([], 121, "Fri")
assert suggest_slots([], 481, "Mon") == []
assert suggest_slots([], 241, "Mon") == []
assert "11:45" in suggest_slots([], 1, "Tue")
assert "11:45" not in suggest_slots([], 16, "Tue")
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 15, "Mon") == []

# Overlapping events are merged; the 15-minute buffers remain in force.
events = [{"start": "10:00", "end": "11:00"},
          {"start": "10:30", "end": "11:15"}]
slots = suggest_slots(events, 15, "Wed")
assert "09:30" in slots and "09:45" not in slots
assert "11:15" not in slots and "11:30" in slots
assert suggest_slots([{"start": "20:00", "end": "21:00"}], 30, "Mon") == monday
assert suggest_slots([{"start": "01:00", "end": "02:00"}], 30, "Mon") == monday

for invalid in [0, -1, 1.5, "15", True, None]:
    try:
        suggest_slots([], invalid, "Mon")
    except ValueError:
        pass
    else:
        raise AssertionError(f"Accepted invalid duration: {invalid!r}")

# Compare against direct interval-conflict checks across random calendars.
rng = random.Random(48)
for _ in range(500):
    intervals = []
    for _ in range(rng.randrange(8)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        intervals.append((start, end))
    events = [{"start": solution.minutes_to_time(s), "end": solution.minutes_to_time(e)}
              for s, e in intervals]
    duration = rng.randrange(1, 600)
    day = rng.choice(["Mon", "Fri", "Sun"])
    expected = []
    for start in range(540, 1020, 15):
        end = start + duration
        if end > 1020 or (day == "Fri" and start > 900):
            continue
        if start < 780 and end > 720:
            continue
        if any(start < e + 15 and end > s - 15 for s, e in intervals):
            continue
        expected.append(solution.minutes_to_time(start))
    assert suggest_slots(events, duration, day) == expected

print("All checks passed (including 500 randomized calendars).")
