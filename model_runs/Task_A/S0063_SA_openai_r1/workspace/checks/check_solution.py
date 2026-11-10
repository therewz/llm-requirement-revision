import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def fmt(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def expected(events, duration):
    busy = [(720, 780)]
    for event in events:
        busy.append(tuple(int(t[:2]) * 60 + int(t[3:]) for t in (event['start'], event['end'])))
    return [fmt(start) for start in range(540, 1020 - duration + 1, 15)
            if not any(start < end and start + duration > begin for begin, end in busy)]

slots = suggest_slots([], 30, '2024-02-02')
assert len(slots) == 26
assert '11:30' in slots and '13:00' in slots and '16:30' in slots
assert '11:45' not in slots and '12:00' not in slots
assert slots == suggest_slots([], 30, '2024-02-02', True)
assert '11:45' in suggest_slots([], 15, '2024-02-01')
assert '11:15' in suggest_slots([], 45, '2024-02-01')
assert '16:45' in suggest_slots([], 1, '2024-02-01')
assert '11:00' in suggest_slots([{'start': '09:00', 'end': '11:00'}], 30, '2024-02-01')
assert '09:00' in suggest_slots([{'start': '09:30', 'end': '10:00'}], 30, '2024-02-01')
assert suggest_slots([{'start': '08:00', 'end': '18:00'}], 30, '2024-02-01') == []
assert suggest_slots([], 241, '2024-02-01') == []
assert suggest_slots([], 0, '2024-02-01') == []
for args in [([], -1, '2024-02-01'), ([], 30, 'invalid'),
             ([{'start': '25:00', 'end': '26:00'}], 30, '2024-02-01'),
             ([{'start': '11:00', 'end': '10:00'}], 30, '2024-02-01')]:
    try:
        suggest_slots(*args)
    except ValueError:
        pass
    else:
        raise AssertionError(args)

rng = random.Random(63)
for _ in range(400):
    events = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        events.append({'start': fmt(start), 'end': fmt(end)})
    original = [dict(e) for e in events]
    duration = rng.randrange(1, 600)
    assert suggest_slots(events, duration, '2024-02-02') == expected(events, duration)
    assert events == original

print('All regression and randomized checks passed.')
