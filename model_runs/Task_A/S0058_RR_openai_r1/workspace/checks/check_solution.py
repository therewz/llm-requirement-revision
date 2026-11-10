import importlib.util
from pathlib import Path
from random import Random

path = Path(__file__).resolve().parents[1] / 'src' / 'solution.py'
spec = importlib.util.spec_from_file_location('solution', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suggest_slots = module.suggest_slots


def event(start, end):
    return {'start': start, 'end': end}


def text(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


expected = [text(t) for t in range(540, 691, 15)]
expected += [text(t) for t in range(780, 991, 15)]
assert suggest_slots([], 30, 'Mon') == expected
assert suggest_slots([], 30, 'M') == expected
for day in ('Tue', 'Wed', 'Thu'):
    assert suggest_slots([], 30, day) == expected
for day in ('Sat', 'Sun'):
    assert suggest_slots([], 30, day) == []
assert '15:00' in suggest_slots([], 120, 'Fri')
assert '15:00' not in suggest_slots([], 121, 'Fri')
assert all(t <= '15:00' for t in suggest_slots([], 1, 'Fri'))
assert '15:15' in suggest_slots([], 30, 'Thu')
assert '13:00' in suggest_slots([], 45, 'Mon')
assert '11:45' in suggest_slots([], 15, 'Mon')
assert '11:45' not in suggest_slots([], 16, 'Mon')
assert suggest_slots([], 241, 'Mon') == []
assert suggest_slots([event('09:00', '17:00')], 30, 'Mon') == []

busy = [event('10:00', '10:30')]
slots = suggest_slots(busy, 30, 'Mon')
assert '09:30' in slots
assert '09:45' not in slots
assert '10:30' not in slots
assert '10:45' in slots

outside = [event('00:00', '09:00'), event('12:00', '13:00'),
           event('17:00', '23:59')]
assert suggest_slots(outside, 30, 'Mon') == expected
assert suggest_slots([event('11:00', '12:00')] + outside, 30, 'Mon') == suggest_slots([event('11:00', '12:00')], 30, 'Mon')
assert '13:00' not in suggest_slots([event('11:00', '13:00')], 30, 'Mon')
assert '13:15' in suggest_slots([event('11:00', '13:00')], 30, 'Mon')
assert '09:30' in suggest_slots([event('08:00', '09:10')], 30, 'Mon')
assert '09:15' not in suggest_slots([event('08:00', '09:10')], 30, 'Mon')

# Compare against an independent, unmerged-event availability check.
rng = Random(58)
for _ in range(500):
    raw = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        raw.append((start, end))
    events = [event(text(s), text(e)) for s, e in raw]
    original = [e.copy() for e in events]
    duration = rng.randrange(1, 301)
    day = rng.choice(['M', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri'])
    relevant = [(s, e) for s, e in raw if (s < 720 and e > 540) or (s < 1020 and e > 780)]
    expected = []
    for t in range(540, 1020, 15):
        end = t + duration
        if not ((540 <= t and end <= 720) or (780 <= t and end <= 1020)):
            continue
        if day == 'Fri' and t > 900:
            continue
        if any(t < e and end > s or e <= t < e + 15 for s, e in relevant):
            continue
        expected.append(text(t))
    assert suggest_slots(events, duration, day) == expected
    assert events == original
    rng.shuffle(events)
    assert suggest_slots(events, duration, day) == expected

print('All targeted checks and 500 randomized cases passed.')
