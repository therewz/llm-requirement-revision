from typing import Dict, List, Union
import math

Number = Union[int, float]


def _valid_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and not math.isnan(value)
        and not math.isinf(value)
        and value >= 0
    )


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited
    capacities, while at least one resource remains partially unallocated.

    Returns True only if all inputs are valid, the total requested amount of each
    resource does not exceed its capacity, and at least one resource has some
    capacity left. Invalid input (empty/missing resources, unknown resources,
    negative or non-numeric amounts, malformed requests) is not feasible -> False.
    """
    if not isinstance(resources, dict) or not resources:
        return False
    for key, value in resources.items():
        if not isinstance(key, str) or not _valid_number(value):
            return False

    if not isinstance(requests, list):
        return False

    used: Dict[str, Number] = {resource: 0 for resource in resources}

    for request in requests:
        if not isinstance(request, dict):
            return False
        for key, value in request.items():
            if not isinstance(key, str) or key not in resources:
                return False
            if not _valid_number(value):
                return False
            used[key] += value
            if used[key] > resources[key]:
                return False

    # At least one resource must remain (partially) unallocated
    return any(used[key] < resources[key] for key in resources)
