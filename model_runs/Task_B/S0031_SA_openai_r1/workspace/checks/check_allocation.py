import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "solution", Path(__file__).resolve().parents[1] / "src" / "solution.py"
)
solution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solution)
feasible = solution.is_allocation_feasible


class AllocationChecks(unittest.TestCase):
    def test_feasibility(self):
        cases = [
            ({}, [], True),
            ({}, [{}], True),
            ({"cpu": 0}, [], True),
            ({"cpu": 0}, [{"cpu": 0}], True),
            ({"cpu": 5}, [{"cpu": 2}, {"cpu": 3}], True),
            ({"cpu": 5}, [{"cpu": 2}, {"cpu": 4}], False),
            ({"cpu": 5, "ram": 8}, [{"cpu": 3, "ram": 8}], True),
            ({"cpu": 5, "ram": 8}, [{"cpu": 1, "ram": 9}], False),
            ({"cpu": 2.5}, [{"cpu": 1.25}, {"cpu": 1.25}], True),
            ({"cpu": 10**400}, [{"cpu": 10**400}], True),
        ]
        for resources, requests, expected in cases:
            with self.subTest(resources=resources, requests=requests):
                self.assertIs(feasible(resources, requests), expected)

    def test_invalid_input(self):
        for resources, requests, error in [
            ([], [], TypeError),
            ({}, {}, TypeError),
            ({"cpu": 1}, [1], TypeError),
            ({"cpu": "1"}, [], TypeError),
            ({"cpu": -1}, [], ValueError),
            ({"cpu": float("inf")}, [], ValueError),
            ({"cpu": 1}, [{"cpu": float("nan")}], ValueError),
            ({"cpu": 1}, [{"cpu": -1}], ValueError),
            ({"cpu": 1}, [{"cpu": "1"}], TypeError),
            ({"cpu": 1}, [{"gpu": 1}], ValueError),
        ]:
            with self.subTest(resources=resources, requests=requests):
                with self.assertRaises(error):
                    feasible(resources, requests)


if __name__ == "__main__":
    unittest.main()
