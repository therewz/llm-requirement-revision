import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py'
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots

expected = [
    f'{minute // 60:02d}:{minute % 60:02d}'
    for minute in range(9 * 60, 17 * 60 - 30 + 1, 15)
    if minute + 30 <= 12 * 60 or minute >= 13 * 60
]
for day in ['Monday', 'Friday', 'friday', 'FRIDAY', '2026-02-20']:
    assert suggest_slots([], 30, day) == expected

assert '15:15' in suggest_slots([], 30, 'Friday')
assert '16:30' in suggest_slots([], 30, 'Friday')
assert '16:45' not in suggest_slots([], 30, 'Friday')
assert suggest_slots([{'start': '09:00', 'end': '15:10'}], 30, 'Friday') == [
    '15:15', '15:30', '15:45', '16:00', '16:15', '16:30'
]
assert suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, 'Friday') == []
assert suggest_slots([], 241, 'Friday') == []
assert suggest_slots([{'start': '15:30', 'end': '16:00'}], 60, 'Friday')[-1] == '16:00'
print('All checks passed.')
