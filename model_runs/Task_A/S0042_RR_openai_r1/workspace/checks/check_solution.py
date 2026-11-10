import random
import sys

sys.path.insert(0, "src")
from solution import suggest_slots, to_minutes, to_time_str


def expect_error(fn, *args):
    try:
        fn(*args)
    except ValueError:
        return
    raise AssertionError((fn.__name__, args))


weekday = suggest_slots([], 30, "Mo")
assert weekday[0] == "09:00"
assert weekday[-1] == "16:30"
assert "09:01" in weekday
assert "11:30" in weekday and "11:31" not in weekday
assert "12:00" not in weekday and "13:00" in weekday
assert weekday == sorted(set(weekday))

friday = suggest_slots([], 30, "Fr")
assert friday[-1] == "15:00"
assert "15:00" in suggest_slots([], 120, "FR")
assert suggest_slots([], 121, "fr")[-1] == "14:59"
assert "17:00" not in suggest_slots([], 1, "Tu")
assert suggest_slots([], 1, "Tu")[-1] == "16:59"
assert suggest_slots([], 241, "We") == []

busy = suggest_slots([{"start": "10:00", "end": "11:00"}], 30, "Th")
assert "09:15" in busy and "09:16" not in busy
assert "11:14" not in busy and "11:15" in busy
assert busy == suggest_slots([{"begin": "10:00", "end": "11:00"}], 30, "Th")
assert "13:00" not in suggest_slots([{"start": "12:00", "end": "13:00"}], 30, "Sa")
assert suggest_slots([{"start": "00:00", "end": "23:59"}], 1, "Su") == []

for value in [0, -1, 1.5, "30", True, None]:
    expect_error(suggest_slots, [], value, "Mo")
for value in ["Friday", "F", "2026-06-12", "XX", " Fr", None, 3]:
    expect_error(suggest_slots, [], 30, value)
for value in ["4pm", "4:00", "09:0", "09:00:00", "24:00", "09:60", " 9:00", "０９:００", None, 930]:
    expect_error(to_minutes, value)
for events in [None, {}, [None], [{}], [{"start": "09:00"}],
               [{"start": "10:00", "end": "09:00"}],
               [{"begin": "10:00", "end": "10:00"}]]:
    expect_error(suggest_slots, events, 30, "Mo")

# Compare against an independent per-minute conflict checker, including
# overlapping, out-of-hours, and lunch events.
rng = random.Random(42)
for _ in range(500):
    spans = []
    for _ in range(rng.randrange(8)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        spans.append((start, end))
    duration = rng.randrange(1, 600)
    day = rng.choice(["Mo", "Fr", "Su"])
    expected = []
    for start in range(9 * 60, 17 * 60):
        end = start + duration
        if end > 17 * 60 or (day == "Fr" and start > 15 * 60):
            continue
        if start < 13 * 60 and end > 12 * 60:
            continue
        if any(start < b + 15 and end > a - 15 for a, b in spans):
            continue
        expected.append(to_time_str(start))
    events = [{"start": to_time_str(a), "end": to_time_str(b)} for a, b in spans]
    original = [event.copy() for event in events]
    assert suggest_slots(events, duration, day) == expected, (events, duration, day)
    assert events == original

print("All scheduling and validation checks passed (including 500 randomized cases).")
