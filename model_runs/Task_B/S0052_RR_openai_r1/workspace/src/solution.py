"""Check whether resource demands fit while leaving some capacity unused."""

from math import isfinite
from typing import Dict, List, Union

Number = Union[int, float]


def _is_nonnegative_finite(amount: Number) -> bool:
    if not isinstance(amount, (int, float)):
        raise ValueError("Resource amounts must be numeric.")
    return amount >= 0 and (not isinstance(amount, float) or isfinite(amount))


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Return whether all demands fit and at least some capacity remains unused.

    Accept either a resource-capacity dictionary and a list of request
    dictionaries, or equal-length lists of capacities and corresponding demands.
    Amounts must be non-negative and finite. Unknown resources, excess demand,
    and allocations with no remaining capacity are infeasible. Inputs are not
    modified.
    """
    if isinstance(resources, list):
        if not isinstance(requests, list):
            raise ValueError("Demands must be a list.")
        if len(resources) != len(requests):
            return False

        has_unused_capacity = False
        for capacity, demand in zip(resources, requests):
            if not _is_nonnegative_finite(capacity) or not _is_nonnegative_finite(demand):
                return False
            if demand > capacity:
                return False
            if demand < capacity:
                has_unused_capacity = True
        return has_unused_capacity

    if not isinstance(resources, dict):
        raise ValueError("Resources must be a dictionary or a list.")

    for capacity in resources.values():
        if not _is_nonnegative_finite(capacity):
            return False

    total_usage: Dict[str, Number] = {r: 0 for r in resources}
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Each request must be a dictionary.")

        for resource_name, amount in request.items():
            if resource_name not in resources:
                return False
            if not _is_nonnegative_finite(amount):
                return False

            total_usage[resource_name] += amount
            if total_usage[resource_name] > resources[resource_name]:
                return False

    return any(total_usage[name] < capacity for name, capacity in resources.items())
