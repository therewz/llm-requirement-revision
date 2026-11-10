import importlib.util
from datetime import date, timedelta
from random import Random

spec = importlib.util.spec_from_file_location("solution", "src/solution.py")
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

monday = suggest_slots([], 30, "Monday")
assert monday[0] == "09:00" and monday[-1] == "16:30"
assert "12:00" in monday and "12:45" in monday
friday = suggest_slots([], 30, "Friday")
assert friday[-1] == "15:00"
assert suggest_slots([], 30, "FRIDAY") == friday
assert suggest_slots([], 30, "2026-06-05") == friday
assert "15:00" in suggest_slots([], 120, "Friday")
assert "15:00" not in suggest_slots([], 121, "Friday")
assert suggest_slots([], 480, "Friday") == ["09:00"]
for duration in (0, -1, 481):
    assert suggest_slots([], duration, "Monday") == []
assert suggest_slots([{"start": "09:00", "end": "17:00"}], 15, "Friday") == []
assert "10:00" in suggest_slots([{"start": "09:00", "end": "10:00"}], 30, "Monday")
assert "09:00" in suggest_slots([{"start": "09:30", "end": "10:00"}], 30, "Monday")
assert "09:15" not in suggest_slots([{"start": "09:30", "end": "10:00"}], 30, "Monday")

# Compare with a direct, unmerged event-overlap check over varied inputs.
rng = Random(17)
for i in range(300):
    raw_events = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(24 * 60)
        end = rng.randrange(start, 24 * 60)
        raw_events.append((start, end))
    events = [{"start": solution._to_hhmm(s), "end": solution._to_hhmm(e)} for s, e in raw_events]
    duration = rng.randrange(1, 500)
    current_date = date(2026, 6, 1) + timedelta(days=i % 7)
    expected = [
        solution._to_hhmm(t)
        for t in range(540, 1020 - duration + 1, 15)
        if (current_date.weekday() != 4 or t <= 900)
        and not any(s < e and t < e and t + duration > s for s, e in raw_events)
    ]
    assert suggest_slots(events, duration, current_date.isoformat()) == expected

print("All scheduling checks passed (including 300 randomized cases).")
