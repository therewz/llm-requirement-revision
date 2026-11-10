"""Feasibility check for resource requests given limited capacities."""

from typing import Dict, List

MAX_RESOURCES = 70


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_allocation_feasible(
    resources: Dict[str, int],
    requests: List[Dict[str, int]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied
    given limited capacities, while leaving at least one unit of
    resource unallocated.

    Args:
        resources : Mapping from resource name to total integer capacity.
        requests : List of requests. Each request is a mapping from
            resource name to the integer amount required.

    Returns:
        True if all requests are fully satisfiable and at least one unit
        of resource remains unallocated, False otherwise.
    """
    if len(resources) > MAX_RESOURCES:
        return False

    # Validate resource capacities (integers, non-negative)
    for capacity in resources.values():
        if not _is_int(capacity) or capacity < 0:
            return False

    total_requested: Dict[str, int] = {r: 0 for r in resources}

    for request in requests:
        for resource, amount in request.items():
            # Resource must exist
            if resource not in resources:
                return False
            # Requests must be non-negative integers
            if not _is_int(amount) or amount < 0:
                return False

            total_requested[resource] += amount
            if total_requested[resource] > resources[resource]:
                return False

    # At least one unit must remain unallocated
    remaining = sum(resources.values()) - sum(total_requested.values())
    return remaining >= 1
