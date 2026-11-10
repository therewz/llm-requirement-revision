import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suggest_slots = module.suggest_slots

friday = '2024-02-02'
normal = suggest_slots([], 30, '2024-02-01')
assert suggest_slots([], 30, friday) == normal
assert suggest_slots([], 30, friday, False) == normal
assert suggest_slots([], 30, friday, True) == normal
assert '15:15' in normal and '16:30' in normal
assert '11:30' in normal and '13:00' in normal
assert not any('11:45' <= start < '13:00' for start in normal)
assert normal == sorted(set(normal))

for duration in (1, 10, 15, 20, 45, 61):
    slots = suggest_slots([], duration, friday)
    assert slots and slots[0] == '09:00'

slots = suggest_slots([{'start': '10:00', 'end': '11:00'}], 30, friday)
assert '09:30' in slots and '11:00' in slots
assert '09:45' not in slots and '10:30' not in slots
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, friday) == []
assert suggest_slots([], 241, friday) == []
assert suggest_slots([], 0, friday) == []
assert suggest_slots([{'start': '08:00', 'end': '09:00'}, {'start': '17:00', 'end': '18:00'}], 30, friday) == normal

# Compare merged/clipped intervals against a direct minute-based overlap oracle.
events = [
    {'start': '15:30', 'end': '18:00'},
    {'start': '08:00', 'end': '09:20'},
    {'start': '10:00', 'end': '10:40'},
    {'start': '10:20', 'end': '11:00'},
]
def minutes(value):
    hour, minute = map(int, value.split(':'))
    return hour * 60 + minute
busy = [(minutes(e['start']), minutes(e['end'])) for e in events] + [(720, 780)]
for duration in (1, 15, 30, 45, 60, 90, 180, 240, 480):
    expected = [
        f'{start // 60:02d}:{start % 60:02d}'
        for start in range(540, 1020 - duration + 1, 15)
        if not any(start < end and start + duration > begin for begin, end in busy)
    ]
    assert suggest_slots(events, duration, friday) == expected

print('All slot checks passed.')
