import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def hhmm(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


slots = suggest_slots([], 60, 'Mon')
assert slots == [hhmm(t) for t in range(540, 961)]
assert '12:00' in slots
assert '09:01' in slots
assert suggest_slots([], 480, 'Mon') == ['09:00']
assert suggest_slots([], 481, 'Mon') == []
assert suggest_slots([{'start': '08:00', 'end': '18:00'}], 1, 'Mon') == []

slots = suggest_slots([{'start': '10:00', 'end': '11:00'}], 60, 'Mon')
assert '09:00' in slots  # Meeting can end at event start.
assert '11:00' in slots  # Meeting can start at event end.
assert '09:01' not in slots
assert '10:59' not in slots

for day in ('Fri', '2026-02-20'):
    slots = suggest_slots([], 30, day)
    assert slots[-1] == '15:00'
    assert all(slot <= '15:00' for slot in slots)
    assert suggest_slots([], 120, day)[-1] == '15:00'
    assert suggest_slots([], 121, day)[-1] == '14:59'
assert suggest_slots([], 30, '2026-02-19')[-1] == '16:30'
assert suggest_slots([{'start': '09:00', 'end': '15:01'}], 30, 'Fri') == []
assert suggest_slots([{'start': '09:00', 'end': '15:00'}], 30, 'Fri') == ['15:00']

# Compare merged-interval behavior with a direct minute-by-minute oracle.
rng = random.Random(42)
for _ in range(200):
    intervals = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(0, 1440)
        end = rng.randrange(start + 1, 1441)
        intervals.append((start, end))
    events = [{'start': hhmm(s), 'end': hhmm(e)} for s, e in intervals]
    original_events = [dict(event) for event in events]
    duration = rng.randrange(1, 550)
    day = rng.choice(['Mon', 'Fri'])
    expected = [
        hhmm(t) for t in range(540, 1020 - duration + 1)
        if (day != 'Fri' or t <= 900)
        and all(t >= end or t + duration <= start for start, end in intervals)
    ]
    assert suggest_slots(events, duration, day) == expected
    assert events == original_events

print('All checks passed (including 200 randomized cases).')
