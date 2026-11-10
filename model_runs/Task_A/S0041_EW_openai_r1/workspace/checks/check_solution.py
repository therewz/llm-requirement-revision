import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
suggest_slots = solution.suggest_slots


class SlotChecks(unittest.TestCase):
    def test_all_slots_and_friday(self):
        expected = [
            "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
            "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
            "16:00", "16:30",
        ]
        self.assertEqual(suggest_slots([], 30, "2026-07-17"), expected)
        self.assertEqual(suggest_slots([], 30, "2026-07-16"), expected)

    def test_short_duration(self):
        self.assertEqual(
            suggest_slots([], 1, "2026-07-17"),
            suggest_slots([], 30, "2026-07-17"),
        )

    def test_boundaries(self):
        slots = suggest_slots(
            [{"start": "10:00", "end": "11:00"}], 60, "2026-07-17"
        )
        self.assertEqual(
            slots, ["09:00", "11:00", "13:00", "13:30", "14:00",
                    "14:30", "15:00", "15:30", "16:00"]
        )

    def test_lunch_crossings(self):
        self.assertEqual(
            suggest_slots([], 90, "2026-07-17"),
            ["09:00", "09:30", "10:00", "10:30", "13:00", "13:30",
             "14:00", "14:30", "15:00", "15:30"],
        )

    def test_overlapping_events(self):
        events = [
            {"start": "10:00", "end": "11:00"},
            {"start": "09:30", "end": "10:30"},
            {"start": "10:15", "end": "10:45"},
        ]
        self.assertEqual(
            suggest_slots(events, 30, "2026-07-17"),
            suggest_slots([{"start": "09:30", "end": "11:00"}],
                          30, "2026-07-17"),
        )

    def test_no_available_slots(self):
        self.assertEqual(suggest_slots([], 241, "2026-07-17"), [])
        self.assertEqual(suggest_slots(
            [{"start": "00:00", "end": "23:59"}], 1, "2026-07-17"
        ), [])

    def test_off_grid_events(self):
        slots = suggest_slots(
            [{"start": "09:10", "end": "10:10"}], 30, "2026-07-17"
        )
        self.assertEqual(slots[0], "10:30")

    def test_invalid_duration(self):
        for duration in [0, -1]:
            with self.assertRaises(ValueError):
                suggest_slots([], duration, "2026-07-17")


if __name__ == "__main__":
    unittest.main()
