import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import suggest_slots, time_to_minutes


def event(start, end):
    return {"start": start, "end": end}


# Acceptance criteria.
assert suggest_slots([], 30, "weekday")[0] == "09:00"
slots = suggest_slots([], 15, "unused")
assert not any(s in slots for s in ("12:00", "12:15", "12:30", "12:45"))
slots = suggest_slots([], 90, "unused")
assert slots[-1] == "15:30" and "15:45" not in slots
slots = suggest_slots([event("09:00", "11:00")], 30, "unused")
assert "10:00" not in slots and "10:30" not in slots and "11:15" in slots
slots = suggest_slots([event("09:30", "10:00")], 30, "unused")
assert "10:00" not in slots and "10:15" in slots
slots = suggest_slots([event("09:00", "09:45"), event("09:45", "10:00")], 15, "unused")
assert slots[0] == "10:00"

# No minimum duration, date format restriction, or Friday cutoff.
for duration in (1, 5, 14, 15, 29, 30, 90, 240, 241, 500):
    expected = suggest_slots([], duration, "arbitrary identifier")
    assert expected == suggest_slots([], duration, "2026-01-02")  # Friday
    assert expected == suggest_slots([], duration, "2026-01-03")  # Saturday
    assert expected == sorted(expected)
    for slot in expected:
        start = time_to_minutes(slot)
        assert start % 15 == 0
        assert any(a <= start and start + duration <= b for a, b in [(540, 720), (780, 1020)])
assert suggest_slots([], 1, "")[-1] == "16:45"
assert suggest_slots([], 241, "") == []

# Outside events are ignored, including events abutting working periods.
outside = [event("07:00", "09:00"), event("12:00", "13:00"), event("17:00", "18:00")]
assert suggest_slots(outside, 30, "") == suggest_slots([], 30, "")
assert suggest_slots([event("08:00", "18:00")], 15, "") == []
assert "13:00" not in suggest_slots([event("11:00", "13:00")], 30, "")
assert "13:00" in suggest_slots([event("11:00", "13:00")], 15, "")
assert "13:15" in suggest_slots([event("11:00", "13:00")], 30, "")
assert "09:15" in suggest_slots([event("08:30", "09:01")], 30, "")
for duration in (0, -1, 1.5):
    try:
        suggest_slots([], duration, "")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid duration accepted")
print("All checks passed")
