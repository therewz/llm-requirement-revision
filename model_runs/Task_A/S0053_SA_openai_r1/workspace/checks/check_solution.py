"""Standard-library checks for meeting slot suggestions."""

import copy
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import solution


def expect(events, duration, day, expected):
    original = copy.deepcopy(events)
    actual = solution.suggest_slots(events, duration, day)
    assert actual == expected, (events, duration, day, actual, expected)
    assert events == original, "input was modified"


hourly = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"]
expect([], 60, "Mon", hourly)
expect([], 60, "Friday", hourly)
expect([], 60, "2026-06-12", hourly)
expect([], 60, "Sat", [])
expect([], 60, "Sunday", [])
expect([], 60, "2026-06-13", [])
expect([], 60, "Holiday", [])
solution.HOLIDAYS.add("2026-06-12")
expect([], 60, "2026-06-12", [])
expect([], 60, "2026-06-11", hourly)
solution.HOLIDAYS.clear()

expect([], 45, "Mon", [
    "09:00", "09:45", "10:30", "11:15",
    "13:00", "13:45", "14:30", "15:15", "16:00",
])
expect([], 180, "Mon", ["09:00", "13:00"])
expect([], 240, "Mon", ["13:00"])
expect([], 241, "Mon", [])
expect([], 480, "Mon", [])
for invalid in (-1, 0, 481, 900):
    try:
        solution.suggest_slots([], invalid, "Mon")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid duration was accepted")

expect([{"start": "09:00", "end": "09:07"}], 60, "Mon", [
    "09:07", "10:07", "13:00", "14:00", "15:00", "16:00",
])
expect([{"start": "09:00", "end": "10:00"}], 60, "Fri", hourly[1:])
expect([{"start": "11:00", "end": "14:00"}], 60, "Mon", [
    "09:00", "10:00", "14:00", "15:00", "16:00",
])
expect([{"start": "08:00", "end": "18:00"}], 1, "Mon", [])
expect([
    {"start": "10:00", "end": "11:00"},
    {"start": "09:30", "end": "10:30"},
    {"start": "08:00", "end": "08:59"},
    {"start": "17:00", "end": "18:00"},
], 60, "Mon", ["11:00", "13:00", "14:00", "15:00", "16:00"])

expect([
    {"start": "09:00", "end": "17:00", "day": "Tue"},
    {"start": "09:00", "end": "17:00", "peaceable": False},
    {"start": "bad", "end": "17:00"},
    {"start": "10:00", "end": "09:00"},
    {"start": "09:00", "end": "09:00"},
    {"start": "25:00", "end": "26:00"},
    {"start": None, "end": "10:00"},
    {},
    None,
    "not an event",
], 60, "Mon", hourly)
expect([
    {"start": "09:00", "end": "17:00", "date": "2026-06-08"},
], 60, "2026-06-15", hourly)
expect([
    {"start": "09:00", "end": "10:00", "date": "2026-06-15"},
], 60, "2026-06-15", hourly[1:])
expect([
    {"start": "09:00", "end": "10:00", "day": "Monday"},
], 60, "2026-06-15", hourly[1:])

# Compare the interval algorithm to a minute-wise earliest-first oracle.
rng = random.Random(53)
for _ in range(500):
    duration = rng.randint(1, 480)
    intervals = []
    events = []
    for _ in range(rng.randint(0, 20)):
        start = rng.randrange(1440)
        end = min(1439, start + rng.randrange(300))
        intervals.append((start, end))
        events.append({"start": solution._to_hhmm(start), "end": solution._to_hhmm(end)})
    blocked = set(range(720, 780))
    for start, end in intervals:
        blocked.update(range(start, end))
    expected = []
    start = 540
    while start + duration <= 1020:
        if blocked.isdisjoint(range(start, start + duration)):
            expected.append(solution._to_hhmm(start))
            start += duration
        else:
            start += 1
    expect(events, duration, "Mon", expected)

print("All meeting slot checks passed (including 500 randomized cases).")
