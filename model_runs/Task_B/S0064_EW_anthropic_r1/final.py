from typing import Dict, List
import numbers
import math


def _valid_amount(value) -> bool:
    """True if value is a numeric (non-bool), finite, non-negative number."""
    if not isinstance(value, numbers.Number) or isinstance(value, bool):
        return False
    try:
        if math.isnan(value) or math.isinf(value):
            return False
        return value >= 0
    except (TypeError, ValueError):
        return False


def is_allocation_feasible(
    resources: Dict[str, numbers.Number],
    requests: List[Dict[str, numbers.Number]]
) -> bool:
    """
    Determines if a set of resource requests can be allocated given available capacities.

    Args:
        resources: Mapping of resource names to available capacities.
        requests: List of requests, each a dict mapping resource names to requested amounts.

    Returns:
        True if the total requested amount for every resource is within its capacity;
        False otherwise (including undefined resources and negative/non-numeric values).

    Raises:
        TypeError: If resources is not a dict or requests is not a list.
        ValueError: If any request is not a dictionary.
    """
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list of dictionaries.")

    # Every request must be a dictionary
    for req in requests:
        if not isinstance(req, dict):
            raise ValueError("Each request must be a dictionary.")

    # Capacities must be numeric and non-negative
    for capacity in resources.values():
        if not _valid_amount(capacity):
            return False

    total_allocated = {res_name: 0 for res_name in resources}

    for req in requests:
        for res_name, amount in req.items():
            if res_name not in resources:
                return False
            if not _valid_amount(amount):
                return False
            total_allocated[res_name] += amount

    for res_name, total in total_allocated.items():
        if total > resources[res_name]:
            return False

    return True
