"""
Determine whether a set of resource requests can be satisfied given limited capacities.
"""

from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Args:
        resources : Dict[str, Number], Mapping from resource name to total available capacity.
        requests : List[Dict[str, Number]], List of requests. Each request is a mapping from resource name to the amount required.

    Returns:
        True if the allocation is feasible, False otherwise.

    """
    remaining = dict(resources)
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Each request must be a dictionary")
        for resource, amount in request.items():
            if not isinstance(amount, (int, float)) or amount < 0:
                raise ValueError("Resource amounts must be non-negative numbers")
            if amount == 0:
                continue
            if resource not in remaining:
                return False
            remaining[resource] -= amount
            if remaining[resource] < 0:
                return False
    return True
