"""
Is-allocation-feasible exercise.

Determine whether a set of resource requests can be satisfied given limited
capacities, while leaving at least one resource not fully consumed.
"""

from typing import Dict, List, Union

Number = Union[int, float]


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Args:
        resources : Mapping from resource name to total available capacity.
        requests : List of requests; each maps resource name to the amount required.

    Returns:
        True if total demand for every resource is within capacity AND at least
        one resource remains with unallocated capacity; False otherwise.
    """
    totals = {name: 0 for name in resources}

    for request in requests:
        for resource, amount in request.items():
            if resource not in resources:
                return False  # unknown resource
            if not _is_number(amount) or amount < 0:
                return False  # invalid amount
            totals[resource] += amount

    for name, capacity in resources.items():
        if not _is_number(capacity) or capacity < 0:
            return False
        if totals[name] > capacity:
            return False

    # At least one resource must remain (partly) unallocated.
    return any(totals[name] < capacity for name, capacity in resources.items())
