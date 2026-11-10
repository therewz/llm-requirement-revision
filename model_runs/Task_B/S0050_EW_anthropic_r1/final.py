""" Stub file for the is allocation feasible exercise.
Implement the function is_allocation_feasible to determine whether
a set of resource requests can be satisfied given limited capacities.
"""

from typing import Dict, List


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_allocation_feasible(
    resources: Dict[str, int],
    requests: List[Dict[str, int]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied
    given limited capacities.

    Args:
        resources : Dict[str, int]
            Mapping from resource name to total available capacity.
        requests : List[Dict[str, int]]
            List of requests. Each request is a mapping from resource
            name to the amount required.

    Returns:
        True if the allocation is feasible, False otherwise.
    """

    # Validate resource capacities (whole, non-negative integers)
    for resource, capacity in resources.items():
        if not _is_int(capacity):
            return False
        if capacity < 0:
            return False

    # Track total requested per resource
    total_requested: Dict[str, int] = {r: 0 for r in resources}

    for request in requests:
        for resource, amount in request.items():

            # Resource must exist
            if resource not in resources:
                return False

            # Validate request amount (whole, non-negative integer)
            if not _is_int(amount):
                return False
            if amount < 0:
                return False

            total_requested[resource] += amount

            # Exceeding capacity is infeasible; using all of it is fine
            if total_requested[resource] > resources[resource]:
                return False

    return True
