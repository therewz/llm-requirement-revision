from typing import Dict, List
from collections.abc import Mapping
import numbers


def is_allocation_feasible(
    resources: Dict[str, numbers.Number],
    requests: List[Dict[str, numbers.Number]]
) -> bool:
    """
    Determine whether the combined requests fit within the available capacities.

    Resource capacities and request amounts must be numeric and non-negative,
    and every requested resource must exist in resources. Exact consumption of
    all available capacity is allowed.

    Returns:
        bool: Whether all requests can be satisfied.

    Raises:
        TypeError: If resources is not a mapping or requests is not a list.
        ValueError: If any request is not a dictionary.
    """
    if not isinstance(resources, Mapping):
        raise TypeError("Resources must be a mapping.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list of dictionaries.")

    # Check every request's structure even if an earlier allocation is invalid.
    if any(not isinstance(req, dict) for req in requests):
        raise ValueError("Each request must be a dictionary.")

    def is_nonnegative_number(value):
        if not isinstance(value, numbers.Number):
            return False
        try:
            # This also rejects NaN and numbers without a real ordering.
            return value >= 0
        except (TypeError, ValueError, ArithmeticError):
            return False

    for capacity in resources.values():
        if not is_nonnegative_number(capacity):
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
