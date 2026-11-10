import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

monday = "2026-02-02"
friday = "2026-02-06"

slots = suggest_slots([], 30, monday)
assert slots[0] == "09:00"
assert slots[-1] == "16:30"
assert len(slots) == 451
assert "12:00" in slots
assert "09:01" in slots

friday_slots = suggest_slots([], 30, friday)
assert friday_slots[-1] == "15:00"
assert friday_slots == [slot for slot in slots if slot <= "15:00"]
assert "15:00" in suggest_slots([], 120, friday)
assert "15:00" not in suggest_slots([], 121, friday)

# Event boundaries may touch; gaps need not start on a quarter hour.
events = [
    {"start": "10:37", "end": "17:00"},
    {"start": "08:00", "end": "10:07"},
]
original = [event.copy() for event in events]
assert suggest_slots(events, 30, monday) == ["10:07"]
assert events == original
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, friday) == []
assert suggest_slots([], 481, monday) == []
assert suggest_slots([], 480, monday) == ["09:00"]
assert suggest_slots([
    {"start": "08:00", "end": "09:00"},
    {"start": "17:00", "end": "18:00"},
], 480, monday) == ["09:00"]

# Overlapping and nested events must all remain blocked.
assert suggest_slots([
    {"start": "09:00", "end": "12:00"},
    {"start": "10:00", "end": "11:00"},
    {"start": "11:00", "end": "16:30"},
], 30, monday) == ["16:30"]

print("All slot checks passed.")
