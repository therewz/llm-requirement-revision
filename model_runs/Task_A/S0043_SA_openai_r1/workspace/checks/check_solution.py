import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suggest_slots = module.suggest_slots

slots = suggest_slots([], 30, 'Mon')
assert len(slots) == 26
assert slots[0] == '09:00' and slots[-1] == '16:30'
assert '11:30' in slots and '11:45' not in slots
assert '12:00' not in slots and '12:45' not in slots and '13:00' in slots
assert suggest_slots([], 30, 'Fri') == slots
assert suggest_slots([], 30, 'Sun') == slots
assert suggest_slots([('07:00', '08:00'), ('17:00', '18:00')], 30, 'Mon') == slots
busy = suggest_slots([('10:00', '11:00')], 30, 'Mon')
assert '09:30' in busy and '09:45' not in busy
assert '10:45' not in busy and '11:00' in busy
assert busy == suggest_slots([{'start': '10:00', 'end': '11:00'}], 30, 'Mon')
assert suggest_slots([('08:00', '09:30')], 30, 'Mon')[0] == '09:30'
assert suggest_slots([('16:00', '18:00')], 30, 'Mon')[-1] == '15:30'
assert suggest_slots([('09:00', '17:00')], 30, 'Mon') == []
assert suggest_slots([], 241, 'Mon') == []
assert suggest_slots([], 240, 'Mon') == ['13:00']
assert suggest_slots([], 180, 'Mon') == ['09:00', '13:00', '13:15', '13:30', '13:45', '14:00']
assert suggest_slots([], 31, 'Mon')[-1] == '16:15'
for duration in (0, -1, 1.5):
    try:
        suggest_slots([], duration, 'Mon')
    except ValueError:
        pass
    else:
        raise AssertionError('invalid duration accepted')

# Compare with a minute-by-minute occupancy oracle, including off-grid events.
rng = random.Random(43)
def fmt(value):
    return f'{value // 60:02d}:{value % 60:02d}'
for _ in range(300):
    intervals = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(1439)
        end = rng.randrange(start + 1, 1440)
        intervals.append((start, end))
    duration = rng.randrange(1, 600)
    occupied = set(range(720, 780))
    for start, end in intervals:
        occupied.update(range(start, end))
    expected = [fmt(t) for t in range(540, 1020 - duration + 1, 15)
                if all(m not in occupied for m in range(t, t + duration))]
    assert suggest_slots([(fmt(s), fmt(e)) for s, e in intervals], duration, 'Mon') == expected
print('All checks passed (including 300 randomized cases).')
