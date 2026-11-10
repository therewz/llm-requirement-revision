import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import suggest_slots, to_minutes


def assert_invalid(*args):
    try:
        suggest_slots(*args)
    except ValueError:
        return
    raise AssertionError(f"Expected invalid input: {args!r}")


# Fridays have the same availability as every other day.
slots = suggest_slots([], 30, "Fr")
assert slots == suggest_slots([], 30, "Mo")
assert "15:15" in slots and "16:30" in slots
assert "17:00" not in slots
assert slots == sorted(set(slots))
assert "11:30" in slots and "13:00" in slots
for slot in slots:
    start = to_minutes(slot)
    assert 540 <= start and start + 30 <= 1020
    assert start + 30 <= 720 or start >= 780

# A break is required before and after existing events.
events = [{"start": "10:00", "end": "10:30"}]
slots = suggest_slots(events, 30, "Tu")
assert "09:15" in slots and "09:30" not in slots
assert "10:30" not in slots and "10:45" in slots

# Overlaps, input order, lunch, and events outside working hours.
events = [
    {"start": "09:45", "end": "10:30"},
    {"start": "09:30", "end": "10:00"},
]
assert suggest_slots(events, 30, "We")[0] == "10:45"
assert suggest_slots(events[::-1], 30, "We") == suggest_slots(events, 30, "We")
assert suggest_slots([{"start": "12:15", "end": "12:45"}], 30, "Th") == suggest_slots([], 30, "Th")
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, "Fr") == []
assert suggest_slots([{"start": "07:00", "end": "08:30"}], 30, "Sa") == suggest_slots([], 30, "Sa")
assert suggest_slots([], 500, "Su") == []
assert "09:00" in suggest_slots([], 1, "fr")

for duration in [0, -1, 1.5, "30", True, None]:
    assert_invalid([], duration, "Mo")
for day in ["Friday", "2026-07-10", "XX", None]:
    assert_invalid([], 30, day)
for time in ["4pm", "04:00 PM", "24:00", "09:60", "9:00", "09:0", "09:00:00", None]:
    assert_invalid([{"start": time, "end": "11:00"}], 30, "Mo")
assert_invalid([{"start": "11:00", "end": "10:00"}], 30, "Mo")
assert_invalid([{"start": "11:00"}], 30, "Mo")
assert_invalid(None, 30, "Mo")

print("All scheduling checks passed.")
