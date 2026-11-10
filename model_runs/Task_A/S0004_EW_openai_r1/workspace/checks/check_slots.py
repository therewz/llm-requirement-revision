import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('solution', Path(__file__).resolve().parents[1] / 'src' / 'solution.py')
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)

expected = [f'{minute // 60:02d}:{minute % 60:02d}' for minute in range(540, 961, 15)]
for day in ('Fri', 'Friday', '2026-07-17', 'Mon'):
    assert solution.suggest_slots([], 60, day) == expected
    assert solution.suggest_slots([{'start': '09:00', 'end': '15:15'}], 60, day) == [
        '15:15', '15:30', '15:45', '16:00'
    ]
    assert solution.suggest_slots([{'start': '09:00', 'end': '17:00'}], 30, day) == []
    assert solution.suggest_slots([], 481, day) == []

assert solution.suggest_slots([{'start': '10:00', 'end': '16:00'}], 60, 'Fri') == ['09:00', '16:00']
assert solution.convert_time_to_mins('09:30') == 570
assert solution.convert_time_to_mins('24:00') is False
print('All checks passed.')
