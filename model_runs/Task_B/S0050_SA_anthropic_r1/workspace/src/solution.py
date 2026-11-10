""" Resource allocation feasibility check.
Determine whether a set of resource requests can be satisfied given limited capacities.
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
            Mapping from resource name to total available (integer) capacity.
        requests : List[Dict[str, int]]
            List of requests. Each request is a mapping from resource
            name to the integer amount required. Resources are not shared
            between requests, so total demand per resource must not exceed
            its capacity.

    Returns:
        True if the allocation is feasible, False otherwise (including for
        invalid input: non-integer or negative amounts, unknown resources).
    """

    # Validate resource capacities (integers only, non-negative)
    for capacity in resources.values():
        if not _is_int(capacity) or capacity < 0:
            return False

    total_requested: Dict[str, int] = {r: 0 for r in resources}

    for request in requests:
        for resource, amount in request.items():
            # Requested resource must exist
            if resource not in resources:
                return False

            # Amount must be a non-negative integer
            if not _is_int(amount) or amount < 0:
                return False

            total_requested[resource] += amount

            if total_requested[resource] > resources[resource]:
                return False

    return True
