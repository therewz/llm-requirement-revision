import sys
import unittest

sys.path.insert(0, 'src')
from solution import is_allocation_feasible


class AllocationChecks(unittest.TestCase):
    def test_feasibility(self):
        cases = [
            ({'cpu': 10}, [{'cpu': 4}, {'cpu': 5}], True),
            ({'cpu': 10}, [{'cpu': 4}, {'cpu': 6}], True),
            ({'cpu': 10}, [{'cpu': 11}], False),
            ({'cpu': 10, 'ram': 4}, [{'cpu': 1, 'ram': 5}], False),
            ({'cpu': 10, 'ram': 4}, [{'cpu': 10, 'ram': 4}], True),
            ({'cpu': 10}, [{'gpu': 0}], False),
            ({'cpu': 10}, [], True),
            ({}, [], True),
            ({}, [{}], True),
            ({}, [{'cpu': 1}], False),
            ({'cpu': 0}, [{'cpu': 0}], True),
            ({'cpu': 1.5}, [{'cpu': 0.5}, {'cpu': 1}], True),
            ({'cpu': 1}, [{'cpu': 1 + 1e-10}], False),
            ({'cpu': 10**400}, [{'cpu': 10**400}], True),
            ({'cpu': 10**20}, [{'cpu': 10**20 + 1}], False),
        ]
        for resources, requests, expected in cases:
            with self.subTest(resources=resources, requests=requests):
                self.assertIs(is_allocation_feasible(resources, requests), expected)

    def test_invalid_requests(self):
        for requests, error in [
            ([1], TypeError),
            ([{'cpu': -1}], ValueError),
            ([{'unknown': -1}], ValueError),
            ([{'unknown': 1}, 'invalid'], TypeError),
            ([{'cpu': 11}, {'cpu': -1}], ValueError),
        ]:
            with self.subTest(requests=requests):
                with self.assertRaises(error):
                    is_allocation_feasible({'cpu': 10}, requests)

    def test_negative_capacity(self):
        with self.assertRaises(ValueError):
            is_allocation_feasible({'cpu': -1}, [])


if __name__ == '__main__':
    unittest.main()
