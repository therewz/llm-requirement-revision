import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from solution import suggest_slots


def clock(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


weekday = suggest_slots([], 30, "Mon")
assert weekday == [clock(m) for m in range(540, 991)]
assert "12:00" in weekday and "12:59" in weekday
assert "09:01" in weekday
assert weekday[-1] == "16:30"

friday = suggest_slots([], 30, "Fri")
assert friday == [clock(m) for m in range(540, 901)]
assert "15:00" in friday and "15:01" not in friday
assert suggest_slots([], 120, "Fri")[-1] == "15:00"
assert suggest_slots([], 121, "Fri")[-1] == "14:59"
assert suggest_slots([], 30, "2026-07-17") == friday
assert suggest_slots([], 30, "2026-07-16") == weekday

slots = suggest_slots([{"start": "10:00", "end": "11:00"}], 30, "Mon")
assert "09:30" in slots and "11:00" in slots
assert "09:31" not in slots and "10:59" not in slots
assert suggest_slots([{"start": "08:00", "end": "18:00"}], 30, "Fri") == []
assert suggest_slots([], 481, "Mon") == []
assert suggest_slots([], 480, "Mon") == ["09:00"]
assert suggest_slots([
    {"start": "07:00", "end": "09:00"},
    {"start": "17:00", "end": "19:00"},
], 30, "Mon") == weekday
assert suggest_slots([
    {"start": "08:00", "end": "09:07"},
    {"start": "09:37", "end": "18:00"},
], 30, "Mon") == ["09:07"]

# Compare with an independent occupied-minute oracle, including unsorted,
# overlapping events and events partly or fully outside working hours.
rng = random.Random(42)
for _ in range(150):
    numeric_events = []
    for _ in range(rng.randrange(9)):
        start = rng.randrange(420, 1140)
        numeric_events.append((start, start + rng.randrange(1, 180)))
    events = [{"start": clock(s), "end": clock(e)} for s, e in numeric_events]
    busy = {m for s, e in numeric_events for m in range(s, e)}
    duration = rng.randrange(1, 550)
    day = rng.choice(["Mon", "Fri"])
    expected = []
    for start in range(540, 1020):
        if start + duration > 1020 or (day == "Fri" and start > 900):
            continue
        if not busy.intersection(range(start, start + duration)):
            expected.append(clock(start))
    assert suggest_slots(events, duration, day) == expected

print("All scheduling checks passed (including 150 randomized cases).")
