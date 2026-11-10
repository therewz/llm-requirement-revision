import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("solution", Path(__file__).resolve().parents[1] / "src" / "solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

weekday_slots = suggest_slots([], 30, "Monday")
for day in ("Fri", "Friday", "FRI ", "2026-05-22"):
    slots = suggest_slots([], 30, day)
    assert slots == weekday_slots
    assert "15:00" in slots
    assert "15:15" in slots
    assert "16:30" in slots
    assert "16:45" not in slots

assert suggest_slots([{"start": "09:00", "end": "15:15"}], 30, "Friday") == [
    "15:15", "15:30", "15:45", "16:00", "16:15", "16:30"
]
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, "Friday") == []
assert suggest_slots([], 481, "Friday") == []
assert suggest_slots([], 0, "Friday") == []
assert suggest_slots([], -15, "Friday") == []
slots = suggest_slots([{"start": "15:30", "end": "16:00"}], 30, "Friday")
assert "15:00" in slots and "16:00" in slots and "16:30" in slots
assert "15:15" not in slots and "15:30" not in slots and "15:45" not in slots
print("All checks passed.")
