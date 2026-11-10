import importlib.util
import random

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)

suggest = solution.suggest_slots
fmt = solution.minutes_to_time

assert suggest([], 1, "2026-06-05") == [fmt(t) for t in range(480, 660)]
assert suggest([], 9, "unused") == ["08:00"]
assert suggest([], 10, "unused") == []
assert suggest([], 8, "unused") == [fmt(t) for t in range(480, 541)]
assert "10:59" in suggest([], 5, "2026-06-05")  # No lunch restriction.
assert "11:00" not in suggest([], 1, "unused")

assert suggest([{"start": "08:00", "end": "11:00"}], 1, "unused") == []
assert suggest([{"start": "07:00", "end": "08:00"}], 1, "unused")[0] == "08:00"
assert suggest([{"start": "09:00", "end": "10:00"}], 1, "unused") == (
    ["08:00"] + [fmt(t) for t in range(600, 660)]
)
assert suggest([{"start": "10:01", "end": "10:02"}], 1, "unused") == (
    [fmt(t) for t in range(480, 542)] + [fmt(t) for t in range(602, 660)]
)
assert suggest(["08:00", "09:00", "10:00"], 1, "unused") == []
assert suggest(["08:00-09:00", "08:30-10:00"], 1, "unused")[0] == "10:00"
assert suggest(["18:00-20:00", "00:00-07:59"], 1, "unused") == suggest([], 1, "unused")
assert suggest(["09:00-10:00"], 1, "unused") == suggest(["09:00"], 1, "unused")
assert solution.time_to_minutes("8:01") == 481

for value in (0, -1, 1.5, "1", True):
    try:
        suggest([], value, "unused")
    except ValueError:
        pass
    else:
        raise AssertionError(value)

for value in ("24:00", "09:60", "-1:00", "09:00\n", None):
    try:
        solution.time_to_minutes(value)
    except ValueError:
        pass
    else:
        raise AssertionError(value)

rng = random.Random(123)
for _ in range(300):
    intervals = []
    for _ in range(rng.randrange(8)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        intervals.append((start, end))
    duration = rng.randrange(1, 12)
    events = [{"start": fmt(s), "end": fmt(e)} for s, e in intervals]
    expected = [
        fmt(t) for t in range(480, 660)
        if t + duration * 60 <= 1020
        and not any(t < e and t + duration * 60 > s for s, e in intervals)
    ]
    before = [dict(e) for e in events]
    assert suggest(events, duration, "unused") == expected
    assert events == before

print("All checks passed")
