import runpy
import unittest

is_allocation_feasible = runpy.run_path('src/solution.py')['is_allocation_feasible']


class AllocationChecks(unittest.TestCase):
    def test_acceptance_cases(self):
        self.assertTrue(is_allocation_feasible({'CPU': 10, 'RAM': 30}, [{'CPU': 5, 'RAM': 20}]))
        self.assertTrue(is_allocation_feasible({'CPU': 10}, [{'CPU': 5}]))
        self.assertFalse(is_allocation_feasible({'RAM': 30}, [{'RAM': 10}, {'RAM': 15}, {'RAM': 10}]))
        self.assertTrue(is_allocation_feasible({'disk': 5.0}, [{'disk': 2.5}, {'disk': 2.5}]))
        self.assertFalse(is_allocation_feasible({'CPU': 10}, [{'GPU': 1}]))
        with self.assertRaises(ValueError):
            is_allocation_feasible({'CPU': -1}, [])

    def test_empty_zero_and_exact_allocations(self):
        self.assertTrue(is_allocation_feasible({}, []))
        self.assertTrue(is_allocation_feasible({}, [{}]))
        self.assertTrue(is_allocation_feasible({'CPU': 0}, [{'CPU': 0}]))
        self.assertTrue(is_allocation_feasible({'CPU': 10}, [{'CPU': 10}]))
        self.assertFalse(is_allocation_feasible({}, [{'GPU': 0}]))

    def test_supported_request_forms_and_identifiers(self):
        self.assertTrue(is_allocation_feasible({'disk': 5.0}, [('disk', 2.5), ('disk', 2.5)]))
        self.assertTrue(is_allocation_feasible({1: 3}, [{1: 1}, (1, 2)]))
        self.assertTrue(is_allocation_feasible({('node', 1): 2}, [(('node', 1), 2)]))
        self.assertFalse(is_allocation_feasible({'CPU': 10}, [('GPU', 1)]))

    def test_invalid_numbers(self):
        for invalid in (-1, float('nan'), float('inf'), float('-inf'), '3', None, True):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError):
                    is_allocation_feasible({'CPU': invalid}, [])
                with self.assertRaises(ValueError):
                    is_allocation_feasible({'CPU': 10}, [{'CPU': invalid}])
        with self.assertRaises(ValueError):
            is_allocation_feasible({'CPU': 1}, [{'CPU': 2}, {'CPU': -1}])

    def test_numeric_precision(self):
        large = 10 ** 400
        self.assertTrue(is_allocation_feasible({'CPU': large}, [{'CPU': large}]))
        self.assertFalse(is_allocation_feasible({'CPU': large}, [{'CPU': large}, {'CPU': 1.0}]))
        self.assertFalse(is_allocation_feasible({'CPU': 2 ** 53}, [{'CPU': 2 ** 53}, {'CPU': 1.0}]))
        self.assertFalse(is_allocation_feasible({'CPU': 1e308}, [{'CPU': 1e308}, {'CPU': 1e308}]))


if __name__ == '__main__':
    unittest.main()
