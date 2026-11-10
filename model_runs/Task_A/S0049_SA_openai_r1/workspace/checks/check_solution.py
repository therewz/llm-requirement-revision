import importlib.util
from pathlib import Path
import random

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

expected_70 = [
    "09:00", "09:15", "09:30", "09:45", "10:00", "10:15", "10:30", "10:45",
    "13:00", "13:15", "13:30", "13:45",
]
for day in ["Monday", "Friday", "2026-02-06", "holiday", "", None]:
    assert suggest_slots([], 70, day) == expected_70
for duration in [0, -1, 361, 500, 1.5, 70.0, None, "70", True, False]:
    assert suggest_slots([], duration, "ignored") == []
assert suggest_slots([], 180, "ignored") == ["09:00"]
assert suggest_slots([], 181, "ignored") == []
assert suggest_slots([{"start": "09:00", "end": "15:00"}], 15, "") == []
assert suggest_slots([{"start": "12:00", "end": "12:00"}], 70, "") == expected_70
assert suggest_slots([{"start": "14:00", "end": "10:00"}], 70, "") == expected_70
assert suggest_slots([
    {"start": "08:00", "end": "08:59"},
    {"start": "15:00", "end": "20:00"},
], 70, "") == expected_70
slots = suggest_slots([{"start": "10:00", "end": "10:30"}], 30, "")
assert "09:30" in slots and "10:30" not in slots and "10:45" in slots
slots = suggest_slots([{"start": "08:00", "end": "09:07"}], 15, "")
assert slots[0] == "09:30"
slots = suggest_slots([{"start": "09:07", "end": "09:26"}], 15, "")
assert slots[0] == "09:45"

# Independent minute-occupancy oracle for shuffled and overlapping events.
rng = random.Random(49)
for _ in range(500):
    events = []
    blocked = set(range(720, 780))
    for _ in range(rng.randrange(12)):
        start = rng.randrange(24 * 60)
        end = rng.randrange(24 * 60)
        events.append({"start": f"{start // 60:02d}:{start % 60:02d}",
                       "end": f"{end // 60:02d}:{end % 60:02d}"})
        if end > start and end > 540 and start < 900:
            blocked.update(range(max(start, 540), min(end + 15, 900)))
    duration = rng.randrange(1, 400)
    expected = []
    for start in range(540, 900, 15):
        if start + duration <= 900 and blocked.isdisjoint(range(start, start + duration)):
            expected.append(f"{start // 60:02d}:{start % 60:02d}")
    original = [dict(event) for event in events]
    assert suggest_slots(events, duration, "ignored") == expected
    assert events == original
    rng.shuffle(events)
    assert suggest_slots(events, duration, "Fri") == expected
    assert suggest_slots(events + events, duration, "holiday") == expected

print("All scheduling checks passed (including 500 randomized cases).")
