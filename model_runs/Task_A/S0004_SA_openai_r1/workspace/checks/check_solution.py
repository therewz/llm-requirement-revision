import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

expected = [f'{minute // 60:02d}:{minute % 60:02d}' for minute in range(540, 991, 15)]
for day in ('Mon', 'Fri', '2026-03-06', 'Sat'):
    assert suggest_slots([], 30, day) == expected

assert suggest_slots([], 480, 'Fri') == ['09:00']
assert suggest_slots([], 481, 'Mon') == []
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, 'Fri') == []
assert suggest_slots([{'start': '09:30', 'end': '16:30'}], 30, 'Fri') == ['09:00', '16:30']
assert suggest_slots([
    {'start': '12:00', 'end': '17:30'},
    {'start': '08:00', 'end': '10:00'},
    {'start': '09:45', 'end': '12:00'},
], 30, 'Mon') == []
assert suggest_slots([
    {'start': '00:00', 'end': '09:00'},
    {'start': '17:00', 'end': '23:59'},
], 30, 'Fri') == expected
assert suggest_slots([{'start': '09:10', 'end': '16:40'}], 15, 'Fri') == ['16:45']
print('All checks passed.')
