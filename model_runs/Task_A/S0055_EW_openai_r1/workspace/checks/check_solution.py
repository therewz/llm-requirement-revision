import contextlib
import io
import random
import runpy

solution = runpy.run_path('src/solution.py')
suggest_slots = solution['suggest_slots']


def call(events, duration, day='2026-07-17'):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        result = suggest_slots(events, duration, day)
    assert stream.getvalue() == str(result) + '\n'
    return result


friday = call([], '30')
assert friday[0] == '09:00' and friday[-1] == '16:30'
assert '15:00' in friday and '15:15' in friday
assert '11:45' in friday
assert not any(t.startswith('12:') for t in friday)
assert call([], 30, '2026-07-18') == friday
assert call([], 30, '2026-07-20') == friday
assert call([], 10)[-1] == '16:45'
assert call([], '1')[-1] == '16:45'
assert call([], 480) == ['09:00']
assert call([], 481) == []
assert call([{'start': '09:00', 'end': '17:00'}], 30) == []
assert call([{'start': '09:00', 'end': '10:00'}], 30)[0] == '10:00'
assert '09:00' in call([{'start': '09:30', 'end': '10:00'}], 30)
assert call([{'start': '09:00'}], '30')[0] == '09:30'
assert call([{'start': '09:00'}], '30') == call([{'start': '09:00', 'end': '09:30'}], 30)

for events in (
    [{'start': '08:59', 'end': '10:00'}],
    [{'start': '16:00', 'end': '17:01'}],
    [{'start': '10:00', 'end': '09:00'}],
    [{'start': '10:00', 'end': '10:00'}],
    [{'start': 600, 'end': '11:00'}],
    [{'end': '11:00'}],
    ['09:00'],
    {'start': '09:00'},
):
    try:
        call(events, 30)
    except ValueError:
        pass
    else:
        raise AssertionError(f'Accepted invalid events: {events}')

for duration in (0, -1, 'zero', '1.5', 1.5, True):
    try:
        call([], duration)
    except ValueError:
        pass
    else:
        raise AssertionError(f'Accepted invalid duration: {duration}')

rng = random.Random(55)
fmt = solution['minutes_to_time']
for _ in range(100):
    intervals = []
    for _ in range(rng.randrange(10)):
        start = rng.randrange(540, 1020)
        end = rng.randrange(start + 1, 1021)
        intervals.append((start, end))
    events = [{'start': fmt(start), 'end': fmt(end)} for start, end in intervals]
    duration = rng.randrange(1, 501)
    occupied = set()
    for start, end in intervals:
        occupied.update(range(start, end))
    expected = [fmt(start) for start in range(540, 1020, 15)
                if start + duration <= 1020 and not 720 <= start < 780
                and not occupied.intersection(range(start, start + duration))]
    assert call(events, duration) == expected
    rng.shuffle(events)
    assert call(events, str(duration)) == expected

print('All slot checks passed (including 100 randomized cases).')
