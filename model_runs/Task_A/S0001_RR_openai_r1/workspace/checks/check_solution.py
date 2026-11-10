import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from solution import suggest_slots


def label(value):
    h, m = divmod(value, 60)
    return f'{h:02d}:{m:02d}'


def reference(events, duration, friday=False):
    def minutes(value):
        h, m = map(int, value.split(':'))
        return h * 60 + m
    busy = [(minutes(e['start']), minutes(e['end'])) for e in events]
    return [label(t) for t in range(540, 1020 - duration + 1)
            if (not friday or t <= 900)
            and all(t + duration <= start or t >= end for start, end in busy)]


slots = suggest_slots([], 30, 'Monday')
assert slots == reference([], 30)
assert '12:00' in slots and '12:59' in slots and '09:01' in slots
assert slots[0] == '09:00' and slots[-1] == '16:30'
assert suggest_slots([], 120, 'FrIdAy')[-1] == '15:00'
assert suggest_slots([], 121, 'Friday')[-1] == '14:59'
assert suggest_slots([], 30, '2026-07-17') == reference([], 30, True)
assert suggest_slots([], 30, '2026-07-20') == reference([], 30)
assert suggest_slots([], 481, 'Monday') == []
assert suggest_slots([], 480, 'Monday') == ['09:00']
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 1, 'Friday') == []
assert suggest_slots([{'start': '09:00', 'end': '15:01'}], 30, 'Friday') == []
assert suggest_slots([{'start': '09:00', 'end': '15:00'}], 30, 'Friday') == ['15:00']

events = [{'start': '09:30', 'end': '10:07'},
          {'start': '10:00', 'end': '11:01'},
          {'start': '07:00', 'end': '09:10'},
          {'start': '16:40', 'end': '18:00'}]
assert suggest_slots(events, 20, 'Monday') == reference(events, 20)
assert events[0] == {'start': '09:30', 'end': '10:07'}

rng = random.Random(42)
for _ in range(300):
    events = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(0, 1400)
        end = rng.randrange(start + 1, 1441)
        events.append({'start': label(start), 'end': label(end)})
    duration = rng.randrange(1, 600)
    for day in ('Monday', 'Friday'):
        assert suggest_slots(events, duration, day) == reference(events, duration, day == 'Friday')

print('All scheduling checks passed (including 600 randomized comparisons).')
