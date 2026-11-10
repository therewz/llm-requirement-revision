import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

for day in ("Friday", "friday", "FRIDAY", "2026-02-06"):
    slots = suggest_slots([], 30, day)
    assert slots == suggest_slots([], 30, "Monday")
    assert "15:00" in slots
    assert "15:15" in slots
    assert "16:30" in slots
    assert "16:45" not in slots

assert "16:45" in suggest_slots([], 15, "Friday")
assert "15:15" in suggest_slots([], 105, "Friday")
assert "15:15" not in suggest_slots([], 106, "Friday")

events = [{"start": "15:30", "end": "16:00"}]
slots = suggest_slots(events, 30, "Friday")
assert "15:00" in slots
assert "15:15" not in slots
assert "15:30" not in slots
assert "16:00" not in slots
assert "16:15" in slots
assert "16:30" in slots
assert slots == suggest_slots(events, 30, "Tuesday")

assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, "Friday") == []
for duration in (0, -1, 481, 1.5):
    assert suggest_slots([], duration, "Friday") == []

# Preserve the existing non-Friday scheduling behavior.
assert "12:00" not in suggest_slots([], 30, "Friday")
assert "13:00" in suggest_slots([], 30, "Friday")
assert suggest_slots([], 480, "Friday") == ["09:00"]
print("All scheduling checks passed.")
