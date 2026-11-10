import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)


def expected(events, duration):
    busy = [(solution.to_minutes(e['start']), solution.to_minutes(e['end'])) for e in events]
    busy.append((720, 780))
    return [solution.to_time_str(t) for t in range(540, 1020, 15)
            if t + duration <= 1020
            and all(t + duration <= start or t >= end for start, end in busy)]


friday = '2026-02-06'
monday = '2026-02-09'
assert '16:30' in solution.suggest_slots([], 30, friday)
assert '15:00' in solution.suggest_slots([], 120, friday)
assert solution.suggest_slots([], 30, friday) == solution.suggest_slots([], 30, monday)
assert '09:00' in solution.suggest_slots([], 1, friday)
assert '16:45' in solution.suggest_slots([], 15, friday)
assert '11:45' in solution.suggest_slots([], 15, friday)
assert '13:00' in solution.suggest_slots([], 15, friday)
assert '09:30' in solution.suggest_slots([{'start': '09:00', 'end': '09:30'}], 30, friday)
assert '09:00' in solution.suggest_slots([{'start': '09:05', 'end': '12:00'}], 5, friday)
assert solution.suggest_slots([{'start': '09:00', 'end': '17:00'}], 1, friday) == []
assert solution.suggest_slots([], 241, friday) == []

for duration in (0, -1):
    try:
        solution.suggest_slots([], duration, friday)
    except ValueError:
        pass
    else:
        raise AssertionError('Nonpositive duration accepted')

rng = random.Random(61)
for _ in range(1500):
    events = []
    for _ in range(rng.randrange(12)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        events.append({'start': solution.to_time_str(start), 'end': solution.to_time_str(end)})
    rng.shuffle(events)
    original = [dict(e) for e in events]
    duration = rng.randint(1, 520)
    assert solution.suggest_slots(events, duration, friday) == expected(events, duration)
    assert events == original

print('All checks passed (including 1500 randomized cases).')
