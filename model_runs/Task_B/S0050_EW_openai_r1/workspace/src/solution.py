"""Determine whether resource requests fit within available capacities."""

from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied
    given limited capacities.

    Args:
        resources : Dict[str, Number]
            Mapping from resource name to total available capacity.
            At most 70 resources are supported; capacities must be
            nonnegative integers.
        requests : List[Dict[str, Number]]
            List of requests. Each request is a mapping from resource
            name to the nonnegative integer amount required.

    Returns:
        True if the allocation is feasible, False otherwise. All
        available capacity may be allocated.
    """

    if len(resources) > 70:
        return False

    # Validate resource capacities; fractional quantities are not supported.
    for resource, capacity in resources.items():
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            return False
        if capacity < 0:
            return False

    # Track total requested per resource, so units cannot share capacity.
    total_requested: Dict[str, Number] = {r: 0 for r in resources}

    for request in requests:
        for resource, amount in request.items():

            # Resource must exist, even if the requested amount is zero.
            if resource not in resources:
                return False

            # Validate request amount.
            if not isinstance(amount, int) or isinstance(amount, bool):
                return False
            if amount < 0:
                return False

            total_requested[resource] += amount

            # Exact-capacity allocations are valid; only excess is rejected.
            if total_requested[resource] > resources[resource]:
                return False

    return True
