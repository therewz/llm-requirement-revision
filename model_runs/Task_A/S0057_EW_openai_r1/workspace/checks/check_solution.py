import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def minutes(value):
    h, m = map(int, value.split(":"))
    return h * 60 + m


# Friday uses the same full working day as every other weekday.
friday = suggest_slots([], 30, "Fri")
assert friday == suggest_slots([], 30, "Mon")
assert friday[0] == "09:00" and friday[-1] == "16:30"
assert "15:15" in friday
assert "12:00" in friday  # No unrequested lunch block.
assert suggest_slots([], 480, "Fri") == ["09:00"]
assert suggest_slots([], 481, "Fri") == []

# Every positive integer duration is accepted, including nonmultiples of 30.
for duration in [1, 5, 15, 29, 31, 45, 61]:
    result = suggest_slots([], duration, "Tue")
    assert result and result[0] == "09:00"
    assert all(minutes(start) + duration <= 17 * 60 for start in result)

assert suggest_slots([], 30, "Sat") == []
assert suggest_slots([], 30, "SUN") == []

# Adjacent meetings need no extra buffer; overlapping events are merged.
events = [
    {"start": "10:00", "end": "11:00"},
    {"start": "09:30", "end": "10:30"},
    {"start": "13:00", "end": "14:00"},
    {"start": "07:00", "end": "08:00"},
    {"start": "18:00", "end": "19:00"},
]
result = suggest_slots(events, 30, "Wed")
assert "09:00" in result
assert "11:00" in result
assert "12:30" in result
assert "14:00" in result
assert result == sorted(set(result))
for start in result:
    start = minutes(start)
    assert 9 * 60 <= start and start + 30 <= 17 * 60
    assert all(start + 30 <= minutes(e["start"]) or start >= minutes(e["end"]) for e in events)
assert suggest_slots([{"start": "08:00", "end": "18:00"}], 1, "Thu") == []

for day in ["", "Monday", "2025-01-03", "123", None]:
    try:
        suggest_slots([], 30, day)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid day accepted")
for duration in [0, -1, 0.5, True, "30"]:
    try:
        suggest_slots([], duration, "Mon")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid duration accepted")

print("All slot checks passed")
