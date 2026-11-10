import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import suggest_slots


for duration in (15, 30, 60, 120):
    friday = suggest_slots([], duration, "Fri")
    assert friday == suggest_slots([], duration, "Mon")
    assert friday == suggest_slots([], duration, "2026-07-17")
    if duration < 120:
        assert any(start > "15:00" for start in friday)
    for start in friday:
        hours, minutes = map(int, start.split(":"))
        assert hours * 60 + minutes + duration <= 17 * 60

assert "16:30" in suggest_slots([], 30, "Fri")
assert "16:00" in suggest_slots([], 60, "Fri")
assert "16:45" not in suggest_slots([], 30, "Fri")

events = [{"start": "15:45", "end": "16:15"}]
slots = suggest_slots(events, 30, "Fri")
assert "16:00" not in slots
assert "16:30" in slots
assert slots == suggest_slots(events, 30, "Mon")
assert "12:00" not in slots
assert "12:30" not in slots
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, "Fri") == []
assert suggest_slots([], 500, "Fri") == []
print("All slot checks passed.")
