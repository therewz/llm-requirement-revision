import importlib.util
import random
from pathlib import Path

spec = importlib.util.spec_from_file_location('solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suggest_slots = module.suggest_slots


def hhmm(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


slots = suggest_slots([], 30, 'Mon')
assert len(slots) == 451
assert slots[0] == '09:00' and slots[-1] == '16:30'
assert '09:01' in slots and '12:00' in slots
assert slots == suggest_slots([], 30, 'Fri')
assert slots == suggest_slots([], 30, '2026-06-12')
assert slots == suggest_slots([], 30, 'Sat')
assert suggest_slots([], 480, 'Mon') == ['09:00']
for duration in (0, -1, 481):
    assert suggest_slots([], duration, 'Mon') == []
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 1, 'Mon') == []

slots = suggest_slots([{'start': '10:00', 'end': '11:00'}], 30, 'Mon')
assert '09:30' in slots and '11:00' in slots
assert '09:31' not in slots and '10:59' not in slots

# Exactly one gap, with unsorted, overlapping and out-of-hours events.
events = [
    {'start': '12:30', 'end': '18:00'},
    {'start': '08:00', 'end': '10:00'},
    {'start': '09:30', 'end': '12:00'},
    {'start': '18:00', 'end': '19:00'},
]
assert suggest_slots(events, 30, 'Fri') == ['12:00']
assert events[0] == {'start': '12:30', 'end': '18:00'}
assert suggest_slots([{'start': '08:00', 'end': '09:00'},
                      {'start': '17:00', 'end': '18:00'}], 480, 'Mon') == ['09:00']

# Compare against independently occupied minutes for varied event layouts.
rng = random.Random(1)
for _ in range(100):
    intervals = [tuple(sorted(rng.sample(range(420, 1141), 2)))
                 for _ in range(rng.randrange(10))]
    events = [{'start': hhmm(start), 'end': hhmm(end)}
              for start, end in intervals]
    duration = rng.randrange(1, 510)
    occupied = set()
    for start, end in intervals:
        occupied.update(range(start, end))
    expected = [hhmm(start) for start in range(540, 1020 - duration + 1)
                if occupied.isdisjoint(range(start, start + duration))]
    assert suggest_slots(events, duration, 'Fri') == expected

print('All checks passed.')
