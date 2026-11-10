from pathlib import Path
import runpy

suggest_slots = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "src" / "solution.py")
)["suggest_slots"]

for events in (
    [],
    [{"start": "15:30", "end": "16:00"}],
    [{"start": "09:00", "end": "17:00"}],
):
    for duration in (15, 30, 60, 120, 480, 600):
        expected = suggest_slots(events, duration, "Mon")
        assert suggest_slots(events, duration, "Fri") == expected
        assert suggest_slots(events, duration, "2026-02-06") == expected

slots = suggest_slots([], 30, "Fri")
assert "15:00" in slots
assert "15:15" in slots
assert "16:30" in slots
assert "16:45" not in slots
assert slots == sorted(slots)

slots = suggest_slots([{"start": "15:30", "end": "16:00"}], 30, "Fri")
assert "15:00" in slots
assert "15:15" not in slots
assert "15:30" not in slots
assert "15:45" not in slots
assert "16:15" in slots
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, "Fri") == []
print("All checks passed.")
