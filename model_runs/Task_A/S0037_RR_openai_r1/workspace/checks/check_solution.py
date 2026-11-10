import copy
import datetime
import importlib.util
import random
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def time_string(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def minutes(value):
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def reference(events, duration, friday):
    busy = [(720, 780)] + [
        (minutes(event["start"]), min(minutes(event["end"]) + 15, 1440))
        for event in events
    ]
    return [
        time_string(start)
        for start in range(540, 1020 - duration + 1, 15)
        if not 720 <= start <= 780
        and (not friday or start <= 900)
        and all(start + duration <= left or start >= right for left, right in busy)
    ]


monday = suggest_slots([], 30, "2025-03-03")
assert monday[0] == "09:00" and monday[-1] == "16:30"
assert "11:30" in monday and "11:45" not in monday
assert all(time not in monday for time in ["12:00", "12:15", "12:45", "13:00"])
assert "13:15" in monday
for day in ["Fri", "fri", "Friday", "2025-03-07"]:
    slots = suggest_slots([], 30, day)
    assert slots[-1] == "15:00"
    assert slots == reference([], 30, True)
assert "15:00" in suggest_slots([], 120, "Fri")
assert "15:00" not in suggest_slots([], 135, "Fri")

booked = [{"start": "09:00", "end": "10:00"}]
assert suggest_slots(booked, 15, "Mon")[0] == "10:15"
assert suggest_slots([{"start": "00:00", "end": "23:59"}], 15, "Mon") == []
assert suggest_slots([], 0, "Mon") == []
assert suggest_slots([], -15, "Mon") == []
assert suggest_slots([], 600, "Mon") == []

# Overlap, adjacency, short gaps, day-edge events, and arbitrary durations.
rng = random.Random(12)
for _ in range(500):
    events = []
    for _ in range(rng.randrange(8)):
        start = rng.randrange(96) * 15
        end = rng.randrange(start // 15 + 1, 97) * 15
        events.append({"start": time_string(start), "end": time_string(end)})
    original = copy.deepcopy(events)
    duration = rng.choice([1, 15, 20, 30, 45, 60, 90, 120, 180, 240, 480])
    friday = rng.choice([True, False])
    result = suggest_slots(events, duration, "Fri" if friday else "Mon")
    assert result == reference(events, duration, friday), (events, duration, result)
    assert events == original
    assert all(minutes(start) % 15 == 0 for start in result)

print("All meeting-slot checks passed.")
