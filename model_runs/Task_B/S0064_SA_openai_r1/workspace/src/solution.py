from collections.abc import Mapping
from typing import Dict, List
import numbers


def is_allocation_feasible(
    resources: Dict[str, numbers.Number],
    requests: List[Dict[str, numbers.Number]]
) -> bool:
    """Return whether the combined requests fit within the resource capacities.

    Capacities and requested amounts must be numeric and non-negative, and
    every requested resource must exist. Invalid values or undefined resources
    make the allocation infeasible. Empty inputs and fully used capacities are
    allowed.

    Raises:
        TypeError: If resources is not a mapping or requests is not a list.
        ValueError: If any request is not a dictionary.
    """
    if not isinstance(resources, Mapping):
        raise TypeError("Resources must be a mapping.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list of dictionaries.")

    # Check every request's structure even if another constraint would fail.
    if any(not isinstance(req, dict) for req in requests):
        raise ValueError("Each request must be a dictionary.")

    def is_nonnegative_number(value):
        if not isinstance(value, numbers.Number):
            return False
        try:
            return value >= 0
        except (TypeError, ValueError, ArithmeticError):
            # For example, complex numbers are not ordered, and NaN is not
            # non-negative (Decimal NaN can raise rather than compare false).
            return False

    if any(not is_nonnegative_number(capacity) for capacity in resources.values()):
        return False

    total_allocated = {res_name: 0 for res_name in resources}
    for req in requests:
        for res_name, amount in req.items():
            if res_name not in resources or not is_nonnegative_number(amount):
                return False
            total_allocated[res_name] += amount
            if total_allocated[res_name] > resources[res_name]:
                return False

    return True
