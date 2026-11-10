from typing import Dict, List, Union
import math

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
        resources: Dictionary mapping resource name to available capacity (>= 0).
        requests: List of dictionaries mapping resource name to requested amount (>= 0).

    Returns:
        True if a valid allocation exists, False otherwise. Invalid input (unknown
        resource, negative or non-numeric amount, malformed request) is not feasible.
    """
    if not isinstance(resources, dict) or not isinstance(requests, list):
        return False

    for key, value in resources.items():
        if not isinstance(key, str) or not _is_number(value):
            return False
        if math.isnan(value) or value < 0:
            return False

    used: Dict[str, Number] = {}

    for request in requests:
        if not isinstance(request, dict):
            return False
        for key, value in request.items():
            if not isinstance(key, str) or key not in resources:
                return False
            if not _is_number(value) or math.isnan(value) or value < 0:
                return False
            used[key] = used.get(key, 0) + value
            if used[key] > resources[key]:
                return False

    return True
