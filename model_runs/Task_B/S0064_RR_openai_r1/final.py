from collections.abc import Mapping
from typing import Dict, List
import numbers


def is_allocation_feasible(
    resources: Dict[str, numbers.Number],
    requests: List[Dict[str, numbers.Number]]
) -> bool:
    """
    Determine whether all requests fit and some resource capacity remains unused.

    Capacities and amounts must be numeric and non-negative. Invalid values,
    undefined resources, over-allocation, or exhausting all capacity return False.
    Resource names may be any keys supported by the resources mapping.

    Raises:
        TypeError: If resources is not a mapping or requests is not a list.
        ValueError: If any request is not a dictionary.
    """
    if not isinstance(resources, Mapping):
        raise TypeError("Resources must be a mapping.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list of dictionaries.")

    # Validate every request's structure, even if an earlier request is infeasible.
    if any(not isinstance(req, dict) for req in requests):
        raise ValueError("Each request must be a dictionary.")

    def is_non_negative_number(value):
        if not isinstance(value, numbers.Number):
            return False
        try:
            # Also rejects NaN and numeric values without an ordering (e.g. complex).
            return value >= 0
        except (TypeError, ValueError, ArithmeticError):
            return False

    for capacity in resources.values():
        if not is_non_negative_number(capacity):
            return False

    total_allocated = {name: 0 for name in resources}
    for req in requests:
        for name, amount in req.items():
            if name not in resources or not is_non_negative_number(amount):
                return False
            total_allocated[name] += amount
            if total_allocated[name] > resources[name]:
                return False

    # Empty or entirely exhausted resources cannot leave any capacity unused.
    return any(total_allocated[name] < resources[name] for name in resources)
