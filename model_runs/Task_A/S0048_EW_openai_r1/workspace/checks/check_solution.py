import importlib.util
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

slots = suggest_slots([], 30, 'Fri')
assert '15:00' in slots and '15:15' in slots and '16:30' in slots
assert '16:45' not in slots
assert slots == suggest_slots([], 30, 'Mon')
assert '11:45' not in slots and '12:00' not in slots and '12:45' not in slots
assert '11:30' in slots and '13:00' in slots
assert suggest_slots([], 481, 'Tue') == []
assert suggest_slots([], 20, 'Wed')[-1] == '16:30'
assert suggest_slots([], 1, 'Thu')[-1] == '16:45'
assert suggest_slots([{'start': '18:00', 'end': '19:00'}], 30, 'Fri') == slots
assert suggest_slots([{'start': '07:00', 'end': '08:00'}], 30, 'Fri') == slots
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, 'Fri') == []

buffered = suggest_slots([{'start': '10:00', 'end': '11:00'}], 30, 'Fri')
assert '09:15' in buffered and '09:30' not in buffered
assert '11:00' not in buffered and '11:15' in buffered
for invalid in (0, -15, 1.5, '30', True):
    try:
        suggest_slots([], invalid, 'Fri')
    except ValueError:
        pass
    else:
        raise AssertionError(invalid)

# Compare to direct interval-conflict checks, including overlapping and
# out-of-hours events and durations that are not multiples of 15.
rng = random.Random(48)
for _ in range(500):
    events = []
    busy = [(720, 780)]
    for _ in range(rng.randrange(8)):
        start = rng.randrange(0, 1439)
        end = rng.randrange(start + 1, 1440)
        events.append({'start': solution.minutes_to_time(start),
                       'end': solution.minutes_to_time(end)})
        busy.append((start - 15, end + 15))
    duration = rng.randrange(1, 600)
    expected = [solution.minutes_to_time(start)
                for start in range(540, 1020 - duration + 1, 15)
                if all(start + duration <= a or start >= b for a, b in busy)]
    assert suggest_slots(events, duration, 'Fri') == expected
print('All scheduling checks passed (including 500 randomized cases).')
