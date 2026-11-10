import importlib.util
from pathlib import Path
from copy import deepcopy
import unittest

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible


class AllocationChecks(unittest.TestCase):
    def test_feasibility(self):
        cases = [
            ({"cpu": 4}, [{"cpu": 4}], True),
            ({"cpu": 4, "memory": 8},
             [{"cpu": 1, "memory": 3}, {"cpu": 3, "memory": 5}], True),
            ({"cpu": 4}, [{"cpu": 2}], True),
            ({"cpu": 4}, [{"cpu": 3}, {"cpu": 2}], False),
            ({"cpu": 1, "memory": 100}, [{"cpu": 2}], False),
            ({"cpu": 4}, [], True),
            ({}, [], True),
            ({}, [{}], True),
            ({"cpu": 0}, [{"cpu": 0}], True),
            ({"cpu": 1.5}, [{"cpu": 0.5}, {"cpu": 1.0}], True),
        ]
        for resources, requests, expected in cases:
            with self.subTest(resources=resources, requests=requests):
                before = deepcopy((resources, requests))
                self.assertIs(feasible(resources, requests), expected)
                self.assertEqual((resources, requests), before)

    def test_validation(self):
        cases = [
            ([], [], TypeError),
            ({"cpu": 4}, {}, TypeError),
            ({"cpu": 4}, [1], TypeError),
            ({"cpu": 4}, [{"unknown": 1}], ValueError),
            ({}, [{"cpu": 1}], ValueError),
            ({"cpu": -1}, [], ValueError),
            ({"cpu": 4}, [{"cpu": -1}], ValueError),
        ]
        for resources, requests, error in cases:
            with self.subTest(resources=resources, requests=requests):
                with self.assertRaises(error):
                    feasible(resources, requests)


if __name__ == "__main__":
    unittest.main()
