import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def time(m):
    return f'{m // 60:02d}:{m % 60:02d}'


def event(start, end):
    return {'start': start, 'end': end}


empty = suggest_slots([], 60, 'Monday')
assert empty == [time(m) for m in range(540, 961)]
assert suggest_slots([], 60, 'Friday') == empty
assert suggest_slots([], 60, '2026-02-06') == empty
assert '15:01' in empty and '16:00' in empty
assert '12:00' in empty
assert suggest_slots([event('09:00', '17:00')], 30, 'Mon') == []
assert suggest_slots([event('09:00', '12:00'), event('13:00', '17:00')], 120, 'Mon') == []
assert suggest_slots([event('09:00', '10:00'), event('11:00', '15:00')], 120, 'Mon') == ['15:00']
assert suggest_slots([event('09:00', '10:07'), event('10:37', '17:00')], 30, 'Fri') == ['10:07']
assert suggest_slots([event('09:00', '10:00'), event('10:00', '16:30')], 30, 'Fri') == ['16:30']
assert suggest_slots([event('18:00', '19:00')], 60, 'Fri') == empty
assert suggest_slots([event('07:00', '08:00')], 60, 'Fri') == empty
assert suggest_slots([], 480, 'Fri') == ['09:00']
assert suggest_slots([], 481, 'Fri') == []
assert len(suggest_slots([], 1, 'Fri')) == 480
assert '16:15' in suggest_slots([], 45, 'Fri')

rng = random.Random(11)
for _ in range(200):
    boundaries = sorted(rng.sample(range(0, 1440), 12))
    intervals = list(zip(boundaries[::2], boundaries[1::2]))
    events = [event(time(s), time(e)) for s, e in intervals]
    rng.shuffle(events)
    original = [e.copy() for e in events]
    duration = rng.randrange(1, 550)
    expected = [time(s) for s in range(540, 1020 - duration + 1)
                if all(s + duration <= a or s >= b for a, b in intervals)]
    assert suggest_slots(events, duration, 'Friday') == expected
    assert events == original

print('All checks passed.')
