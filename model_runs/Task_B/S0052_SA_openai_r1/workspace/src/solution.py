"""Check whether resource demands fit within fixed, independent capacities."""

import math
from typing import Dict, List, Union

Number = Union[int, float]


def _valid_amount(amount: Number) -> bool:
    """Validate numeric amounts without converting arbitrarily large integers."""
    if not isinstance(amount, (int, float)):
        raise ValueError("Resource amounts must be numeric.")
    return amount >= 0 and (
        not isinstance(amount, float) or math.isfinite(amount)
    )


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether all requests fit without borrowing between resources.

    Resources may be a dictionary of capacities, with requests supplied as a
    list of dictionaries. Requests are aggregated by resource name, and every
    referenced resource must exist, even when its requested amount is zero.

    Alternatively, resources and requests may both be lists of amounts. These
    lists must have equal lengths and are compared position by position.

    Amounts must be non-negative, finite numbers. Empty requests are feasible
    when the capacities are valid (and, for lists, the lengths match).
    """
    if isinstance(resources, list):
        if not isinstance(requests, list):
            raise ValueError("Requests must be a list.")
        if len(resources) != len(requests):
            return False
        for capacity, demand in zip(resources, requests):
            if not _valid_amount(capacity) or not _valid_amount(demand):
                return False
            if demand > capacity:
                return False
        return True

    if not isinstance(resources, dict):
        raise ValueError("Resources must be a dictionary or a list.")

    # Validate unused capacities too: invalid resources cannot be allocated.
    for capacity in resources.values():
        if not _valid_amount(capacity):
            return False

    total_usage: Dict[str, Number] = {}
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Each request must be a dictionary.")
        for resource_name, amount in request.items():
            if resource_name not in resources:
                return False
            if not _valid_amount(amount):
                return False
            used = total_usage.get(resource_name, 0) + amount
            if used > resources[resource_name]:
                return False
            total_usage[resource_name] = used

    return True
