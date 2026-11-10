import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

monday = "2026-02-02"
friday = "2026-02-06"

slots = suggest_slots([], 60, monday)
assert slots[0] == "09:00" and slots[-1] == "16:00"
assert "12:00" in slots and "12:30" in slots
assert "11:30" in slots  # Meetings may span noon.

slots = suggest_slots([], 60, friday)
assert slots[-1] == "15:00"
assert all(slot <= "15:00" for slot in slots)
assert "15:00" in suggest_slots([], 120, friday)
assert "15:00" not in suggest_slots([], 135, friday)

slots = suggest_slots([{"start": "10:00", "end": "11:00"}], 60, monday)
assert "09:00" in slots and "11:00" in slots
assert "09:15" not in slots and "10:45" not in slots

assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, monday) == []
assert suggest_slots([], 481, monday) == []
assert suggest_slots([], 480, monday) == ["09:00"]
assert suggest_slots([
    {"start": "08:00", "end": "09:00"},
    {"start": "17:00", "end": "18:00"},
], 60, monday) == suggest_slots([], 60, monday)

# Check boundaries, unsorted events, lunch availability, and the Friday cap
# against an independent minute-based reference.
events = [
    {"start": "14:10", "end": "14:50"},
    {"start": "08:30", "end": "09:30"},
    {"start": "10:00", "end": "11:00"},
    {"start": "10:45", "end": "11:15"},
    {"start": "16:30", "end": "18:00"},
]
def minutes(value):
    hour, minute = map(int, value.split(":"))
    return 60 * hour + minute

for day in (monday, friday):
    for duration in (15, 30, 60, 90, 120, 480, 600):
        expected = []
        for start in range(9 * 60, 17 * 60 - duration + 1, 15):
            if day == friday and start > 15 * 60:
                continue
            if any(start < minutes(event["end"]) and
                   start + duration > minutes(event["start"])
                   for event in events):
                continue
            expected.append(f"{start // 60:02d}:{start % 60:02d}")
        assert suggest_slots(events, duration, day) == expected

print("All checks passed.")
