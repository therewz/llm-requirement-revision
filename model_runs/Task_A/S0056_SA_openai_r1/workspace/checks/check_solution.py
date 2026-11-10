import copy
import random
import runpy

module = runpy.run_path('src/solution.py')
suggest = module['suggest_slots']
parse = module['time_to_minutes']
format_time = module['minutes_to_time']


def reference(events, duration):
    busy = [(parse(e['start']), parse(e['end'])) for e in events]
    busy.append((720, 780))
    return [format_time(start) for start in range(540, 1020 - duration + 1)
            if all(start + duration <= left or start >= right
                   for left, right in busy)]


empty = suggest([], 30, 'Monday')
assert len(empty) == 362
assert empty[0] == '09:00' and empty[-1] == '16:30'
assert '09:01' in empty
assert '11:30' in empty and '11:31' not in empty
assert '12:00' not in empty and '13:00' in empty
assert len(suggest([], 1, 'Tuesday')) == 420
assert suggest([], 241, 'Wednesday') == []
assert suggest([], 240, 'Thursday') == ['13:00']
assert suggest([], 30, 'Friday') == empty
assert suggest([], 30, '2026-06-12') == empty
assert suggest([], 30, 'Saturday') == empty
assert suggest([{'start': '09:00', 'end': '17:00'}], 1, 'Sunday') == []

outside = [{'start': '07:00', 'end': '09:00'},
           {'start': '17:00', 'end': '20:00'}]
assert suggest(outside, 30, 'Monday') == empty
adjacent = [{'start': '10:00', 'end': '11:00'}]
slots = suggest(adjacent, 30, 'Monday')
assert '09:30' in slots and '11:00' in slots
assert '09:31' not in slots and '10:59' not in slots

random.seed(56)
for _ in range(300):
    events = []
    for _ in range(random.randrange(15)):
        start = random.randrange(1439)
        end = random.randrange(start + 1, 1440)
        events.append({'start': format_time(start), 'end': format_time(end)})
    before = copy.deepcopy(events)
    duration = random.randrange(1, 550)
    actual = suggest(events, duration, 'Monday')
    assert actual == reference(events, duration)
    assert events == before
    random.shuffle(events)
    assert actual == suggest(events, duration, 'Friday')

for duration in [0, -1, 1.5, True, '30']:
    try:
        suggest([], duration, 'Monday')
    except ValueError:
        pass
    else:
        raise AssertionError(f'Accepted invalid duration: {duration!r}')

print('All scheduling checks passed.')
