import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from solution import suggest_slots


def event(start, end):
    return {"start": start, "end": end}


monday = "2026-04-06"
friday = "2026-04-10"
slots = suggest_slots([], 30, monday)
assert len(slots) == 451
assert slots[:2] == ["09:00", "09:01"]
assert slots[-1] == "16:30"
assert "12:00" in slots
assert suggest_slots([], 30, friday) == slots
assert suggest_slots([], 480, monday) == ["09:00"]
assert suggest_slots([], 481, monday) == []
assert suggest_slots([], 0, monday) == []
assert suggest_slots([], -1, monday) == []
assert suggest_slots([event("09:00", "17:00")], 30, monday) == []
assert suggest_slots([event("08:00", "18:00")], 30, monday) == []
assert suggest_slots([event("07:00", "09:00"), event("17:00", "19:00")], 30, monday) == slots

# The only gap is off the quarter-hour grid and exactly the meeting duration.
events = [event("09:37", "17:00"), event("08:00", "09:07")]
assert suggest_slots(events, 30, monday) == ["09:07"]

# Overlapping and nested busy periods, supplied out of order.
events = [event("10:00", "11:00"), event("09:45", "10:15"),
          event("10:15", "10:30")]
slots = suggest_slots(events, 30, monday)
assert "09:15" in slots
assert "09:16" not in slots
assert "10:59" not in slots
assert "11:00" in slots

# Compare against a direct occupied-minute oracle over several calendars.
calendars = [[], events, [event("08:45", "09:17"), event("12:04", "12:43"),
                         event("16:52", "18:00")]]
for calendar in calendars:
    occupied = set()
    for entry in calendar:
        def minutes(value):
            h, m = map(int, value.split(":"))
            return h * 60 + m
        occupied.update(range(minutes(entry["start"]), minutes(entry["end"])))
    for duration in [1, 7, 30, 61, 240, 480, 481]:
        expected = [f"{start // 60:02d}:{start % 60:02d}"
                    for start in range(540, 1020 - duration + 1)
                    if not occupied.intersection(range(start, start + duration))]
        assert suggest_slots(calendar, duration, friday) == expected

print("All checks passed.")
