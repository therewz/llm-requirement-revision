import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suggest_slots = module.suggest_slots

expected = [
    f"{minute // 60:02d}:{minute % 60:02d}"
    for minute in list(range(540, 691, 15)) + list(range(780, 991, 15))
]
assert suggest_slots([], 30, "Mon") == expected
for day in ("Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
    assert suggest_slots([], 30, day) == expected

outside = [
    {"start": "00:00", "end": "09:00"},
    {"start": "17:00", "end": "23:59"},
]
assert suggest_slots(outside, 30, "Mon") == expected
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, "Mon") == []
assert suggest_slots([], 241, "Mon") == []
assert suggest_slots([], 240, "Mon") == ["13:00"]
assert suggest_slots([], 180, "Mon") == [
    "09:00", "13:00", "13:15", "13:30", "13:45", "14:00"
]

slots = suggest_slots([{"start": "10:00", "end": "11:00"}], 30, "Mon")
assert "09:30" in slots and "11:00" in slots
assert not set(["09:45", "10:00", "10:15", "10:30", "10:45"]) & set(slots)
assert "11:30" in slots and "13:00" in slots and "16:30" in slots

# Partial overlaps with the workday and arbitrary positive durations.
events = [
    {"start": "08:00", "end": "09:20"},
    {"start": "16:40", "end": "18:00"},
]
slots = suggest_slots(events, 17, "Fri")
assert slots[0] == "09:30" and slots[-1] == "16:15"
assert "11:45" not in slots
assert suggest_slots([], 1, "Sun")[-1] == "16:45"
assert suggest_slots([], 10**20, "Mon") == []
print("All meeting slot checks passed.")
