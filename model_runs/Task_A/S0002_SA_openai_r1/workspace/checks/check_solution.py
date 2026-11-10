import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


def time(minutes):
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


empty = suggest_slots([], 30, 'Mon')
assert len(empty) == 31
assert empty[0] == '09:00' and empty[-1] == '16:30'
assert '12:00' in empty and '12:45' in empty
assert suggest_slots([], 30, 'Fri') == empty
assert suggest_slots([], 30, '2026-03-06') == empty
assert suggest_slots([], 30, 'Sat') == empty

slots = suggest_slots([{'start': '10:00', 'end': '11:00'}], 30, 'Tue')
assert '09:30' in slots and '11:00' in slots
assert '09:45' not in slots and '10:45' not in slots
assert suggest_slots([{'start': '08:00', 'end': '18:00'}], 15, 'Mon') == []
assert suggest_slots([], 481, 'Mon') == []
assert suggest_slots([], 480, 'Mon') == ['09:00']
assert suggest_slots([
    {'start': '08:00', 'end': '09:00'},
    {'start': '17:00', 'end': '18:00'},
], 30, 'Mon') == empty

# Compare the interval check against a minute-by-minute occupancy oracle.
rng = random.Random(42)
for _ in range(300):
    occupied = set()
    events = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(7 * 60, 19 * 60)
        end = rng.randrange(start + 1, 20 * 60)
        events.append({'start': time(start), 'end': time(end)})
        occupied.update(range(start, end))
    duration = rng.randrange(1, 550)
    expected = [
        time(start) for start in range(9 * 60, 17 * 60, 15)
        if start + duration <= 17 * 60
        and not occupied.intersection(range(start, start + duration))
    ]
    assert suggest_slots(events, duration, 'Fri') == expected

print('All checks passed (including 300 randomized schedules).')
