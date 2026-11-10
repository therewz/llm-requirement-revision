import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def clock(n):
    return f'{n // 60:02d}:{n % 60:02d}'


def events(*intervals):
    return [{'start': start, 'end': end} for start, end in intervals]


assert suggest_slots([], 60, 'Monday') == [clock(n) for n in range(540, 961)]
assert suggest_slots([], 60, 'Friday') == suggest_slots([], 60, '2026-06-19')
assert '12:00' in suggest_slots([], 60, 'Friday')
assert '16:00' in suggest_slots([], 60, 'Friday')
assert suggest_slots([], 480, 'Sunday') == ['09:00']
assert suggest_slots([], 481, 'Monday') == []
assert suggest_slots(events(('09:00', '17:00')), 30, 'Monday') == []
assert suggest_slots(events(('09:00', '12:00'), ('13:00', '17:00')), 120, 'Monday') == []
assert suggest_slots(events(('09:00', '10:00'), ('11:00', '15:00')), 120, 'Monday') == ['15:00']
assert suggest_slots(events(('09:00', '10:00'), ('10:00', '16:30')), 30, 'Monday') == ['16:30']
assert suggest_slots(events(('09:00', '10:07'), ('10:44', '17:00')), 37, 'Monday') == ['10:07']
assert suggest_slots(events(('00:00', '09:00'), ('17:00', '23:59')), 480, 'Monday') == ['09:00']
assert suggest_slots(events(('18:00', '19:00')), 30, 'Monday')[-1] == '16:30'
assert suggest_slots(events(('08:00', '10:00'), ('16:00', '20:00')), 360, 'Monday') == ['10:00']
for duration in (0, -30):
    try:
        suggest_slots([], duration, 'Monday')
    except ValueError:
        pass
    else:
        raise AssertionError('Nonpositive duration accepted')

rng = random.Random(42)
for _ in range(300):
    boundaries = sorted(rng.sample(range(1440), rng.randrange(0, 20, 2)))
    intervals = list(zip(boundaries[::2], boundaries[1::2]))
    calendar = [{'start': clock(a), 'end': clock(b)} for a, b in intervals]
    rng.shuffle(calendar)
    original = [dict(event) for event in calendar]
    duration = rng.randint(1, 550)
    expected = [clock(s) for s in range(540, 1020 - duration + 1)
                if all(s + duration <= a or s >= b for a, b in intervals)]
    assert suggest_slots(calendar, duration, 'Friday') == expected
    assert calendar == original

print('All example and randomized checks passed.')
