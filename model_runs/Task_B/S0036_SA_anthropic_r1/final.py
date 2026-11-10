from typing import Dict, List, Union
import math

Number = Union[int, float]


def _valid_number(value) -> bool:
    """True for a finite, non-negative int/float (bools excluded)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return not (math.isnan(value) or math.isinf(value)) and value >= 0


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited
    capacities. Resources are shared (pooled) across all requests.

    Returns True if the summed demand for every resource is within its
    available amount (exact matches are allowed; an empty request list is
    fine). Returns False if the inputs are invalid (wrong types, negative or
    non-finite values, a request that is not a dict), if a request names a
    resource that does not exist, or if capacity is exceeded.
    """
    if not isinstance(resources, dict) or not isinstance(requests, list):
        return False

    for r_key, r_val in resources.items():
        if not isinstance(r_key, str) or not _valid_number(r_val):
            return False

    total_used = {resource: 0 for resource in resources}

    for request in requests:
        if not isinstance(request, dict):
            return False
        for req_key, req_val in request.items():
            if not isinstance(req_key, str) or not _valid_number(req_val):
                return False
            if req_key not in resources:
                return False
            total_used[req_key] += req_val
            if total_used[req_key] > resources[req_key]:
                return False

    return True
