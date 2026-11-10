import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

slots = suggest_slots([], 30, 'Monday')
assert slots[0] == '09:00' and slots[-1] == '16:30'
assert len(slots) == 451
assert '12:00' in slots and '12:59' in slots
assert '09:07' in slots

for friday in ('Fri', 'Friday', 'FRI ', '2026-02-06'):
    slots = suggest_slots([], 30, friday)
    assert slots[-1] == '15:00'
    assert '15:01' not in slots
    assert len(slots) == 361
    assert suggest_slots([], 120, friday)[-1] == '15:00'
    assert suggest_slots([], 121, friday)[-1] == '14:59'

assert suggest_slots([], 480, 'Monday') == ['09:00']
for duration in (-10, 0, 481):
    assert suggest_slots([], duration, 'Friday') == []
assert suggest_slots([{'start': '08:00', 'end': '18:00'}], 30, 'Monday') == []
assert suggest_slots([
    {'start': '08:00', 'end': '09:07'},
    {'start': '09:37', 'end': '18:00'},
], 30, 'Monday') == ['09:07']
assert '12:00' not in suggest_slots([{'start': '12:00', 'end': '13:00'}], 30, 'Monday')
assert suggest_slots([
    {'start': '09:00', 'end': '12:00'},
    {'start': '13:00', 'end': '17:00'},
], 60, 'Friday') == ['12:00']

# Compare merged-interval handling with a direct overlap check.
rng = random.Random(42)
def hhmm(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'

for _ in range(200):
    intervals = []
    for _ in range(rng.randrange(15)):
        start = rng.randrange(480, 1081)
        end = rng.randrange(start, 1141)
        intervals.append((start, end))
    events = [{'start': hhmm(s), 'end': hhmm(t)} for s, t in intervals]
    duration = rng.randrange(1, 501)
    friday = rng.choice([False, True])
    expected = [hhmm(s) for s in range(540, 1020 - duration + 1)
                if (not friday or s <= 900)
                and not any(s < t and b < s + duration for b, t in intervals if t > b)]
    assert suggest_slots(events, duration, 'Fri' if friday else 'Mon') == expected

print('All checks passed.')
