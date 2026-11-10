import itertools
import runpy

solution = runpy.run_path("src/solution.py")
suggest_slots = solution["suggest_slots"]
to_minutes = solution["time_to_minutes"]

monday = "2026-06-01"
friday = "2026-06-05"
assert suggest_slots([], 45, monday)[0] == "09:00"
assert suggest_slots([], 15, monday)[-1] == "16:45"
assert "16:00" in suggest_slots([], 60, monday)
assert "16:15" not in suggest_slots([], 60, monday)
assert all(not ("12:00" <= s < "13:00") for s in suggest_slots([], 15, monday))
assert "11:45" not in suggest_slots([], 30, monday)
assert "13:00" in suggest_slots([], 30, monday)

# Friday's cutoff applies to starts, not ends.
for duration in (5, 15, 30, 60, 120):
    slots = suggest_slots([], duration, friday)
    assert "15:00" in slots
    assert all(s <= "15:00" for s in slots)
assert "15:00" not in suggest_slots([], 121, friday)
assert "15:15" in suggest_slots([], 30, monday)
assert "09:00" in suggest_slots([], 5, monday)
assert suggest_slots([], 481, monday) == []
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, friday) == []
for duration in (0, -1):
    try:
        suggest_slots([], duration, monday)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected positive-duration validation")

events = [
    {"start": "14:00", "end": "15:00"},
    {"start": "10:00", "end": "10:45"},
    {"start": "10:30", "end": "11:00"},
    {"start": "07:00", "end": "08:00"},
    {"start": "18:00", "end": "19:00"},
]
for day in (monday, friday):
    for duration in (1, 5, 15, 30, 45, 60, 120, 181, 480):
        expected = []
        blocked = [(to_minutes(e["start"]), to_minutes(e["end"])) for e in events]
        blocked.append((720, 780))
        for start in range(540, 1020, 15):
            if start + duration > 1020 or (day == friday and start > 900):
                continue
            if all(start + duration <= a or start >= b for a, b in blocked):
                expected.append(f"{start // 60:02d}:{start % 60:02d}")
        for permutation in itertools.permutations(events):
            assert suggest_slots(list(permutation), duration, day) == expected
assert "15:00" in suggest_slots(events, 30, friday)
assert "13:30" in suggest_slots(events, 30, monday)
assert "13:45" not in suggest_slots(events, 30, monday)
assert "14:00" not in suggest_slots(events, 30, monday)
print("All checks passed")
