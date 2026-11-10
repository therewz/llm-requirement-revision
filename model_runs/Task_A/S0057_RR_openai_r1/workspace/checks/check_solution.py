from pathlib import Path
import runpy
import random

suggest_slots = runpy.run_path(str(Path(__file__).resolve().parents[1] / "src" / "solution.py"))["suggest_slots"]

assert suggest_slots([], 60, "Mon")[0] == "09:00"
assert suggest_slots([], 60, "Mon")[-1] == "16:00"
assert "12:00" in suggest_slots([], 60, "Mon")
assert suggest_slots([], 1, "Tue")
assert suggest_slots([], 17, "Wed")
assert suggest_slots([], 480, "Thu") == ["09:00"]
assert suggest_slots([], 481, "Thu") == []
assert suggest_slots([], 60, "Fri")[-1] == "15:00"
assert suggest_slots([], 120, "FRI")[-1] == "15:00"
assert suggest_slots([], 180, "Fri")[-1] == "14:00"
assert suggest_slots([], 60, "Sat") == []
assert suggest_slots([], 60, "Sun") == []
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 30, "Mon") == []
assert suggest_slots([{"start": "09:00", "end": "10:00"}], 30, "Mon")[0] == "10:00"
assert "09:30" in suggest_slots([{"start": "10:00", "end": "11:00"}], 30, "Mon")
assert suggest_slots([{"start": "09:00", "end": "15:01"}], 30, "Fri") == []
assert suggest_slots([{"start": "09:00", "end": "15:00"}], 120, "Fri") == ["15:00"]
assert "15:00" not in suggest_slots([{"start": "16:00", "end": "17:00"}], 120, "Fri")
for invalid in ["2026-04-03", "Friday", "Mo", "xxx", None]:
    try:
        suggest_slots([], 30, invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(invalid)
for invalid in [0, -1, 1.5, True]:
    try:
        suggest_slots([], invalid, "Mon")
    except ValueError:
        pass
    else:
        raise AssertionError(invalid)


def text(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def minutes(text):
    h, m = map(int, text.split(":"))
    return 60 * h + m


rng = random.Random(57)
for _ in range(200):
    intervals = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(0, 1439)
        intervals.append((start, rng.randrange(start + 1, 1440)))
    events = [{"start": text(s), "end": text(e)} for s, e in intervals]
    original = [dict(event) for event in events]
    duration = rng.randrange(1, 600)
    day = rng.choice(["Mon", "Fri"])
    result = suggest_slots(events, duration, day)
    assert result == sorted(set(result))
    assert events == original
    for slot in result:
        start = minutes(slot)
        assert 540 <= start and start + duration <= 1020
        assert day != "Fri" or start <= 900
        assert all(start + duration <= s or start >= e for s, e in intervals)

print("All slot checks passed")
