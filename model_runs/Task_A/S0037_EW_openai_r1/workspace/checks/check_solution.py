import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def minutes(time):
    hour, minute = map(int, time.split(":"))
    return hour * 60 + minute


for duration in (15, 30, 45, 60, 120):
    baseline = suggest_slots([], duration, "Mon")
    for day in ("Fri", "Friday", "2026-06-12", "2026-06-11"):
        assert suggest_slots([], duration, day) == baseline
    assert baseline == sorted(baseline)
    for time in baseline:
        start = minutes(time)
        assert start % 15 == 0
        assert 9 * 60 <= start and start + duration <= 17 * 60
        assert start + duration <= 12 * 60 or start >= 13 * 60

assert "15:15" in suggest_slots([], 30, "Fri")
assert "16:30" in suggest_slots([], 30, "2026-06-12")
assert "16:45" in suggest_slots([], 15, "Fri")
assert "17:00" not in suggest_slots([], 15, "Fri")

events = [
    {"start": "14:00", "end": "15:00"},
    {"start": "14:30", "end": "15:30"},
]
original = [dict(event) for event in events]
slots = suggest_slots(events, 30, "Fri")
assert events == original
assert "13:30" in slots
assert "15:30" not in slots
assert "15:45" in slots
assert all(minutes(slot) + 30 <= 14 * 60 or minutes(slot) >= 15 * 60 + 45 for slot in slots)

# A gap shorter than the requested duration cannot hold a meeting.
events = [
    {"start": "09:00", "end": "10:00"},
    {"start": "10:30", "end": "11:00"},
]
assert "10:15" not in suggest_slots(events, 30, "Mon")
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 15, "Fri") == []
assert suggest_slots([], 600, "Mon") == []
print("All checks passed")
