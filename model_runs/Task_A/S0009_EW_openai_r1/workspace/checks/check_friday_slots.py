import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

friday = "2026-06-12"
monday = "2026-06-15"
slots = suggest_slots([], 30, friday)
assert slots == suggest_slots([], 30, monday)
assert "15:15" in slots
assert "16:30" in slots
assert "16:45" not in slots
assert "12:00" not in slots
assert slots == sorted(slots)
assert suggest_slots([{"start": "09:00", "end": "16:00"}], 60, friday) == ["16:00"]
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, friday) == []
assert suggest_slots([], 30, "invalid") == []
assert suggest_slots([], 481, friday) == []

busy = [{"start": "15:30", "end": "16:00"}]
slots = suggest_slots(busy, 30, friday)
assert "15:00" in slots
assert "15:15" not in slots
assert "15:30" not in slots
assert "15:45" not in slots
assert "16:00" in slots
print("All checks passed.")
