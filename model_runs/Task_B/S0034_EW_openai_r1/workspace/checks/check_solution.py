import itertools
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.solution import is_allocation_feasible


class AllocationChecks(unittest.TestCase):
    def test_feasibility(self):
        cases = [
            ({"CPU": 10}, [{"CPU": 4}, {"CPU": 6}], True),
            ({"CPU": 8}, [{"CPU": 4}, {"CPU": 6}], False),
            ({"CPU": 8, "Memory": 30}, [{"CPU": 8, "Memory": 32}], False),
            ({"CPU": 8}, [{"Memory": 1}], False),
            ({"CPU": 8}, [{"Memory": 0}], False),
            ({"CPU": 8}, [], True),
            ({"CPU": 0}, [{"CPU": 0}], True),
            ({"CPU": 8, "Memory": 30}, [{"CPU": 8, "Memory": 30}], True),
            ({}, [], True),
            ({}, [{}], True),
            ({}, [{"CPU": 1}], False),
            ({"": 1}, [{"": 1}], True),
            ({"CPU": float("inf")}, [{"CPU": 100}], True),
            ({"CPU": 10 ** 400}, [{"CPU": 10 ** 400}], True),
            ({"CPU": 0.5}, [{"CPU": 0.25}, {"CPU": 0.25}], True),
        ]
        for resources, requests, expected in cases:
            with self.subTest(resources=resources, requests=requests):
                self.assertIs(is_allocation_feasible(resources, requests), expected)

    def test_validation(self):
        for requests in [[[]], [1], [{"other": 1}, []]]:
            with self.assertRaises(ValueError):
                is_allocation_feasible({"CPU": 1}, requests)
        for resources, requests in [
            ({"CPU": -1}, []),
            ({"CPU": 1}, [{"CPU": -1}]),
            ({"CPU": float("nan")}, []),
            ({"CPU": 1}, [{"CPU": float("nan")}]),
        ]:
            with self.assertRaises(ValueError):
                is_allocation_feasible(resources, requests)
        for resources, requests in [
            ({"CPU": "1"}, []),
            ({"CPU": 1}, [{"CPU": "1"}]),
        ]:
            with self.assertRaises(TypeError):
                is_allocation_feasible(resources, requests)

    def test_small_allocations(self):
        for ca, cb, a1, b1, a2, b2 in itertools.product(range(3), repeat=6):
            resources = {"a": ca, "b": cb}
            requests = [{"a": a1, "b": b1}, {"a": a2, "b": b2}]
            self.assertIs(
                is_allocation_feasible(resources, requests),
                a1 + a2 <= ca and b1 + b2 <= cb,
            )
            self.assertEqual(resources, {"a": ca, "b": cb})
            self.assertEqual(requests, [{"a": a1, "b": b1}, {"a": a2, "b": b2}])


if __name__ == "__main__":
    unittest.main()
