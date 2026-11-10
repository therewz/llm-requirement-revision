import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.solution import suggest_slots, time_to_minutes


def event(start, end):
    return {"start": start, "end": end}


# Acceptance criteria.
assert suggest_slots([], 30, "Monday")[0] == "09:00"
slots = suggest_slots([], 15, "weekday")
assert all(t not in slots for t in ("12:00", "12:15", "12:30", "12:45"))
assert suggest_slots([], 90, "weekday")[-1] == "15:30"
assert "15:45" not in suggest_slots([], 90, "weekday")
slots = suggest_slots([event("09:00", "11:00")], 30, "weekday")
assert "10:00" not in slots and "10:30" not in slots and "11:15" in slots
slots = suggest_slots([event("09:30", "10:00")], 30, "weekday")
assert "10:00" not in slots and "10:15" in slots
slots = suggest_slots([event("09:00", "09:45"), event("09:45", "10:00")], 15, "weekday")
assert slots[0] == "10:00"

# No special Friday policy, date parsing, or minimum 15-minute duration.
for duration in (1, 5, 14, 15, 29, 30, 90, 240, 241):
    expected = suggest_slots([], duration, "2026-07-02")
    assert suggest_slots([], duration, "2026-07-03") == expected
    assert suggest_slots([], duration, "Friday") == expected
    assert suggest_slots([], duration, "") == expected
    assert expected == sorted(expected)
    for slot in expected:
        start = time_to_minutes(slot)
        assert start % 15 == 0
        assert 540 <= start < start + duration <= 720 or 780 <= start < start + duration <= 1020
assert "16:30" in suggest_slots([], 30, "Friday")
assert "16:45" in suggest_slots([], 1, "Friday")
assert suggest_slots([], 241, "any") == []

# Outside events are ignored, but partial working-hour overlaps still block.
assert suggest_slots([event("07:00", "09:00"), event("12:00", "13:00"), event("17:00", "18:00")], 30, "any") == suggest_slots([], 30, "any")
assert suggest_slots([event("08:00", "09:30")], 30, "any")[0] == "09:45"
assert suggest_slots([event("08:00", "18:00")], 15, "any") == []
slots = suggest_slots([event("09:30", "10:00")], 29, "any")
assert "10:00" in slots
for invalid in (0, -1, 1.5):
    try:
        suggest_slots([], invalid, "any")
    except ValueError:
        pass
    else:
        raise AssertionError(f"Accepted invalid duration {invalid}")

print("All scheduling checks passed.")
