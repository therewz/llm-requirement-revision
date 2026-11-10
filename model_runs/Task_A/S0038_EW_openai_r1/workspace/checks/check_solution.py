import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import suggest_slots


def minutes(time):
    hour, minute = map(int, time.split(':'))
    return hour * 60 + minute


def reference(events, duration):
    busy = [(minutes(e['start']), minutes(e['end'])) for e in events]
    busy.append((720, 780))
    result = []
    for start in range(540, 1020, 15):
        end = start + duration
        if end <= 1020 and all(end <= left or start >= right for left, right in busy):
            result.append(f'{start // 60:02d}:{start % 60:02d}')
    return result


baseline = suggest_slots([], 30, 'Mon')
assert '11:30' in baseline
assert '12:00' not in baseline
assert '13:00' in baseline
assert '16:30' in baseline
for day in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'):
    assert suggest_slots([], 30, day) == baseline
assert suggest_slots([{'start': '00:00', 'end': '09:00'},
                      {'start': '17:00', 'end': '23:59'}], 30, 'Fri') == baseline
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, 'Mon') == []
assert suggest_slots([], 241, 'Mon') == []
assert suggest_slots([], 240, 'Fri') == ['13:00']
assert suggest_slots([], 180, 'Mon')[0] == '09:00'
slots = suggest_slots([{'start': '10:00', 'end': '10:30'}], 30, 'Fri')
assert '09:30' in slots and '10:30' in slots
assert '09:45' not in slots and '10:00' not in slots

cases = [[], [{'start': '08:45', 'end': '09:20'}],
         [{'start': '16:40', 'end': '18:00'}],
         [{'start': '10:07', 'end': '10:38'},
          {'start': '10:15', 'end': '11:00'},
          {'start': '13:00', 'end': '13:45'}]]
for events in cases:
    for duration in (1, 7, 15, 16, 30, 45, 60, 180, 240, 241, 480, 1000):
        for day in ('Mon', 'Fri', 'Sun'):
            assert suggest_slots(events, duration, day) == reference(events, duration)
print('All meeting-slot checks passed.')
