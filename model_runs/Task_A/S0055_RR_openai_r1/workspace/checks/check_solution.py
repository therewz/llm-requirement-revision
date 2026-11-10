import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from solution import suggest_slots, time_to_minutes, minutes_to_time


def call(events, duration, day='2026-02-09'):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = suggest_slots(events, duration, day)
    assert output.getvalue() == repr(result) + '\n'
    return result


slots = call([], '30')
assert slots[0] == '09:00' and slots[-1] == '16:30'
assert '11:45' in slots and '13:00' in slots
assert not any(s.startswith('12:') for s in slots)
assert len(slots) == 27

friday = call([], '60', '2026-02-13')
assert '15:00' in friday and friday[-1] == '15:00'
assert '15:15' not in friday
assert '15:00' in call([], 120, '2026-02-13')
assert call([], 30, '2026-02-14') == slots

for duration in (1, 10, 15, 20, 45):
    assert call([], str(duration))
assert call([], 481) == []
assert call([{'start': '09:00', 'end': '17:00'}], 15) == []

# Boundary contact is not a conflict, and no post-event buffer is imposed.
events = [{'start': '10:00', 'end': '11:00'},
          {'start': '14:00', 'end': '14:30'}]
original = [dict(event) for event in events]
slots = call(events, 30)
assert '09:30' in slots and '11:00' in slots and '14:30' in slots
assert '09:45' not in slots and '10:30' not in slots
assert slots == call(events[::-1], 30)
assert events == original
assert call([{'start': '10:00'}], '30') == call(
    [{'start': '10:00', 'end': '10:30'}], 30)

for events in (
    [{'start': '08:59', 'end': '10:00'}],
    [{'start': '16:00', 'end': '17:01'}],
    [{'start': '18:00', 'end': '19:00'}],
    [{'start': '11:00', 'end': '10:00'}],
    [{'start': '10:00', 'end': '10:00'}],
    [{'start': 900}],
    [{}],
    ['09:00'],
    {'start': '09:00'},
    (),
):
    try:
        call(events, 30)
    except ValueError:
        pass
    else:
        raise AssertionError(events)

for duration in (0, -10, 'abc', '1.5', 1.5, True, None):
    try:
        call([], duration)
    except ValueError:
        pass
    else:
        raise AssertionError(duration)

# Cross-check every start against an independent occupancy grid.
events = [{'start': '09:17', 'end': '10:03'},
          {'start': '13:11', 'end': '14:47'},
          {'start': '10:01', 'end': '11:00'}]
busy = set()
for ev in events:
    busy.update(range(time_to_minutes(ev['start']), time_to_minutes(ev['end'])))
for day, friday in [('2026-02-09', False), ('2026-02-13', True)]:
    for duration in (1, 17, 30, 47, 120, 480, 600):
        expected = []
        for start in range(540, 1020, 15):
            if start + duration > 1020 or 720 <= start < 780:
                continue
            if friday and start > 900:
                continue
            if busy.isdisjoint(range(start, start + duration)):
                expected.append(minutes_to_time(start))
        assert call(events, duration, day) == expected

print('All checks passed.')
