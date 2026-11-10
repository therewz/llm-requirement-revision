import contextlib
import importlib.util
import io
import random

spec = importlib.util.spec_from_file_location('solution', 'src/solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)


def call(events, duration, day='2026-01-10'):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        result = solution.suggest_slots(events, duration, day)
    assert out.getvalue() == str(result) + '\n'
    return result


slots = call([], '30')
assert slots[:3] == ['09:00', '09:15', '09:30']
assert slots[-1] == '16:30'
assert not any('12:' in slot for slot in slots)
assert '11:45' in slots  # A meeting may span lunch.
assert call([], '30', '2026-01-09') == slots  # No Friday cutoff.
assert call([], '30', '2026-01-11') == slots  # No weekend exclusion.
assert call([], '15')[-1] == '16:45'
assert call([], '5')[-1] == '16:45'
assert call([], '45')[-1] == '16:15'
assert call([], '480') == ['09:00']
assert call([], '481') == []
assert call([{'start': '09:00', 'end': '17:00'}], '30') == []
assert call([{'start': '10:00'}], '30') == call([{'start': '10:00', 'end': '10:30'}], '30')
slots = call([{'start': '10:00', 'end': '11:00'}], 30)
assert '09:30' in slots and '11:00' in slots
assert '09:45' not in slots and '10:45' not in slots

for events in (
    {},
    ['09:00'],
    [{}],
    [{'start': 900}],
    [{'start': '08:45', 'end': '09:15'}],
    [{'start': '16:45', 'end': '17:15'}],
    [{'start': '11:00', 'end': '10:00'}],
):
    try:
        call(events, '30')
    except ValueError:
        pass
    else:
        raise AssertionError(events)

for duration in ('0', '-1', 'abc', '30.5', 1.5, None):
    try:
        call([], duration)
    except ValueError:
        pass
    else:
        raise AssertionError(duration)

rng = random.Random(1234)
for _ in range(200):
    intervals = []
    for _ in range(rng.randrange(8)):
        start = rng.randrange(540, 1020)
        end = rng.randrange(start + 1, 1021)
        intervals.append((start, end))
    events = [{'start': solution.minutes_to_time(a), 'end': solution.minutes_to_time(b)}
              for a, b in intervals]
    duration = rng.randrange(1, 600)
    expected = [solution.minutes_to_time(start)
                for start in range(540, 1020 - duration + 1, 15)
                if not 720 <= start < 780
                and all(start + duration <= a or start >= b for a, b in intervals)]
    assert call(events, str(duration)) == expected
    rng.shuffle(events)
    assert call(events, duration) == expected

print('All checks passed.')
