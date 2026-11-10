import itertools
import sys
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from solution import is_allocation_feasible


class AllocationTests(unittest.TestCase):
    def test_capacity_and_independence(self):
        self.assertTrue(is_allocation_feasible({"CPU": 10}, [{"CPU": 4}, {"CPU": 6}]))
        self.assertFalse(is_allocation_feasible({"CPU": 8}, [{"CPU": 10}]))
        self.assertFalse(is_allocation_feasible(
            {"CPU": 8, "Memory": 30}, [{"CPU": 8, "Memory": 32}]))
        self.assertTrue(is_allocation_feasible(
            {"CPU": 8, "Memory": 30}, [{"CPU": 8, "Memory": 30}]))
        self.assertTrue(is_allocation_feasible({"CPU": 10}, [{"CPU": 1}]))

    def test_missing_resources(self):
        self.assertFalse(is_allocation_feasible({"CPU": 10}, [{"GPU": 1}]))
        self.assertFalse(is_allocation_feasible({"CPU": 10}, [{"GPU": 0}]))
        self.assertFalse(is_allocation_feasible({}, [{"CPU": 1}]))

    def test_empty_inputs(self):
        self.assertTrue(is_allocation_feasible({"CPU": 10}, []))
        self.assertTrue(is_allocation_feasible({}, []))
        self.assertTrue(is_allocation_feasible({}, [{}]))
        self.assertTrue(is_allocation_feasible({"CPU": 0}, [{"CPU": 0}]))
        self.assertTrue(is_allocation_feasible({"": 1}, [{"": 1}]))

    def test_bad_requests(self):
        for request in ([], [1], "CPU", None, 1):
            with self.subTest(request=request), self.assertRaises(ValueError):
                is_allocation_feasible({"CPU": 10}, [request])
        with self.assertRaises(ValueError):
            is_allocation_feasible({"CPU": 10}, [{"GPU": 1}, []])

    def test_invalid_values(self):
        for value, error in ((-1, ValueError), ("1", TypeError), (float("nan"), ValueError)):
            with self.subTest(value=value):
                with self.assertRaises(error):
                    is_allocation_feasible({"CPU": value}, [])
                with self.assertRaises(error):
                    is_allocation_feasible({"CPU": 10}, [{"CPU": value}])

    def test_numeric_values(self):
        for capacity, requests in (
            (10**500, [10**500]),
            (float("inf"), [1, float("inf")]),
            (Decimal("1.0"), [Decimal("0.3"), Decimal("0.7")]),
            (Fraction(1), [Fraction(1, 3), Fraction(2, 3)]),
        ):
            with self.subTest(capacity=capacity):
                self.assertTrue(is_allocation_feasible(
                    {"CPU": capacity}, [{"CPU": amount} for amount in requests]))

    def test_small_exhaustive(self):
        for cpu, memory, a, b, c, d in itertools.product(range(3), repeat=6):
            self.assertEqual(
                is_allocation_feasible(
                    {"CPU": cpu, "Memory": memory},
                    [{"CPU": a, "Memory": b}, {"CPU": c, "Memory": d}]),
                a + c <= cpu and b + d <= memory,
            )


if __name__ == "__main__":
    unittest.main()
