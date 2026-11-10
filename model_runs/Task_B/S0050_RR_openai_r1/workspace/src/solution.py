"""Determine whether resource requests can be fully allocated."""

from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether all requests can be met with capacity left over.

    Capacities and requested amounts must be nonnegative integers (not
    booleans). There may be at most 70 resource units in total. Requests
    must name existing resources, and their combined demand cannot exceed
    any resource's capacity. At least one unit, across all resource types,
    must remain unallocated, even when there are no requests.
    """
    total_capacity = 0
    for capacity in resources.values():
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            return False
        if capacity < 0:
            return False
        total_capacity += capacity

    if total_capacity > 70:
        return False

    # Accumulate demand so that separate requests cannot share units.
    total_requested: Dict[str, Number] = {r: 0 for r in resources}

    for request in requests:
        for resource, amount in request.items():
            if resource not in resources:
                return False
            if not isinstance(amount, int) or isinstance(amount, bool):
                return False
            if amount < 0:
                return False

            total_requested[resource] += amount
            if total_requested[resource] > resources[resource]:
                return False

    return sum(total_requested.values()) < total_capacity
