import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("solution", Path(__file__).resolve().parents[1] / "src" / "solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest = solution.suggest_slots

# Acceptance criteria.
assert suggest([], 30, "Monday")[0] == "09:00"
assert not any("12:00" <= slot < "13:00" for slot in suggest([], 15, "Monday"))
assert suggest([], 90, "Monday")[-1] == "15:30"
assert "15:45" not in suggest([], 90, "Monday")
slots = suggest([{"start": "09:00", "end": "11:00"}], 30, "Monday")
assert "10:00" not in slots and "10:30" not in slots and "11:15" in slots
slots = suggest([{"start": "09:30", "end": "10:00"}], 30, "Monday")
assert "10:00" not in slots and "10:15" in slots
slots = suggest([{"start": "09:00", "end": "09:45"}, {"start": "09:45", "end": "10:00"}], 15, "Monday")
assert slots[0] == "10:00"

# Positive durations below 15 are valid, but starts remain on the grid.
for duration in (1, 5, 14, 15, 16, 29, 30, 90):
    slots = suggest([], duration, "arbitrary identifier")
    assert slots == sorted(slots)
    assert all(solution.time_to_minutes(s) % 15 == 0 for s in slots)
    assert all(any(a <= solution.time_to_minutes(s) and solution.time_to_minutes(s) + duration <= b
                   for a, b in ((540, 720), (780, 1020))) for s in slots)
assert suggest([], 241, "anything") == []

# Friday cutoff concerns start time, not end time, and includes 15:00.
for day in ("Friday", "fri", " FRIDAY ", "2026-04-03"):
    for duration in (1, 15, 30, 90, 120):
        slots = suggest([], duration, day)
        assert slots[-1] == "15:00", (day, duration, slots)
        assert all(s <= "15:00" for s in slots)
assert suggest([], 30, "2026-04-02")[-1] == "16:30"
assert suggest([], 30, "Saturday")[-1] == "16:30"

# Outside-hours events are ignored; partial overlaps still block.
assert suggest([{"start": "07:00", "end": "09:00"},
                {"start": "12:00", "end": "13:00"},
                {"start": "17:00", "end": "18:00"}], 30, "Monday") == suggest([], 30, "Monday")
assert "09:00" not in suggest([{"start": "08:00", "end": "09:15"}], 15, "Monday")
assert suggest([{"start": "08:00", "end": "18:00"}], 15, "Friday") == []
print("All scheduling checks passed.")
