import sys
from pathlib import Path
from copy import deepcopy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from solution import suggest_slots

MONDAY = "2026-02-02"
FRIDAY = "2026-02-06"
expected = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
]
assert suggest_slots([], 30, MONDAY) == expected
assert suggest_slots([], 1, MONDAY) == expected
assert suggest_slots([], 10, MONDAY) == expected
assert suggest_slots([], 30, FRIDAY) == [s for s in expected if s <= "15:00"]
assert suggest_slots([], 120, FRIDAY)[-1] == "15:00"
assert suggest_slots([], 240, FRIDAY) == ["13:00"]
assert suggest_slots([], 241, MONDAY) == []
assert suggest_slots([], 600, MONDAY) == []

# Touching boundaries are allowed; overlap with lunch or events is not.
events = [{"start": "10:00", "end": "11:00"}]
slots = suggest_slots(events, 60, MONDAY)
assert "09:00" in slots and "11:00" in slots
assert "09:30" not in slots and "10:00" not in slots
assert "11:30" not in slots and "12:00" not in slots and "12:30" not in slots
assert "13:00" in slots

# Overlapping events act as a single blocked interval, regardless of order.
events = [
    {"start": "10:00", "end": "11:00"},
    {"start": "09:30", "end": "10:30"},
    {"start": "09:45", "end": "10:15"},
]
original = deepcopy(events)
assert suggest_slots(events, 30, MONDAY) == suggest_slots(
    [{"start": "09:30", "end": "11:00"}], 30, MONDAY
)
assert events == original
assert suggest_slots([{"start": "08:00", "end": "18:00"}], 30, FRIDAY) == []
assert suggest_slots([{"start": "07:00", "end": "08:00"}], 30, MONDAY) == expected
for duration in (0, -1):
    try:
        suggest_slots([], duration, MONDAY)
    except ValueError:
        pass
    else:
        raise AssertionError("Nonpositive duration should be rejected")
print("All checks passed.")
