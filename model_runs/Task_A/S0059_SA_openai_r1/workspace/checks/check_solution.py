import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suggest_slots = module.suggest_slots


def time_string(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def oracle(events, duration):
    def minutes(value):
        hour, minute = map(int, value.split(':'))
        return hour * 60 + minute
    intervals = [(minutes(e['start']), minutes(e['end'])) for e in events]
    return [time_string(start) for start in range(540, 1020 - duration + 1)
            if all(start + duration <= a or start >= b for a, b in intervals)]


assert suggest_slots([], 480, 'not a date') == ['09:00']
assert suggest_slots([], 481, '') == []
assert len(suggest_slots([], 1, 'Friday')) == 480
assert len(suggest_slots([], 30, '2026-05-01')) == 451
assert '12:30' in suggest_slots([], 7, 'arbitrary day')
assert '16:53' in suggest_slots([], 7, 'Friday')
events = [{'start': '10:00', 'end': '11:00'}]
slots = suggest_slots(events, 30, '')
assert '09:30' in slots and '11:00' in slots
assert '09:31' not in slots and '10:59' not in slots
assert suggest_slots([{'start': '08:00', 'end': '18:00'}], 1, '') == []
assert suggest_slots([{'start': '08:00', 'end': '09:00'},
                      {'start': '17:00', 'end': '18:00'}], 480, '') == ['09:00']

rng = random.Random(59)
for _ in range(1000):
    events = []
    for _ in range(rng.randrange(15)):
        a, b = sorted(rng.sample(range(1440), 2))
        events.append({'start': time_string(a), 'end': time_string(b)})
    rng.shuffle(events)
    duration = rng.randint(1, 550)
    original = [dict(event) for event in events]
    assert suggest_slots(events, duration, 'any day') == oracle(events, duration)
    assert events == original

for duration in [0, -1]:
    try:
        suggest_slots([], duration, '')
    except ValueError:
        pass
    else:
        raise AssertionError('Nonpositive duration accepted')

print('All checks passed, including 1,000 randomized comparisons.')
