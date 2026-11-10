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
        resources : Mapping from resource name to total available capacity.
        requests : List of requests. Each request is a mapping from resource name to the amount required.

    Returns:
        True if the total demand for every resource fits within its capacity, False otherwise.
    """
    total_requested: Dict[str, Number] = {}

    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Request is not a dictionary.")

        for name, amount in request.items():
            if amount > 0:
                total_requested[name] = total_requested.get(name, 0) + amount

    # Can't ask for missing resources or exceed capacity
    for name, total_amount in total_requested.items():
        if name not in resources or total_amount > resources[name]:
            return False

    return True
