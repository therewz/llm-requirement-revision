from typing import Dict, List, Union
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Resources are shared (pooled) across requests. The allocation is feasible only if
    no resource is over-used AND at least one resource retains some unallocated
    capacity (i.e. the allocation does not consume everything available).

    Raises:
        TypeError: If input types are incorrect.
        ValueError: If numeric values are invalid (negative, NaN, infinite).

    Returns:
        bool: True if feasible and something remains unallocated, False otherwise
        (including requests that are not dicts or that name nonexistent resources).
    """

    # Type validations
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    # Check resource keys and values
    for r_key, r_val in resources.items():
        if not isinstance(r_key, str):
            raise TypeError("Resource keys must be strings")
        if not isinstance(r_val, (int, float)):
            raise TypeError("Resource values must be numbers")
        if r_val < 0 or math.isnan(r_val) or math.isinf(r_val):
            raise ValueError("Resource values must be non-negative finite numbers")

    # Initialize usage tracker
    total_used = {resource: 0 for resource in resources}

    # Process requests
    for request in requests:
        if not isinstance(request, dict):
            return False  # each request must be a dictionary
        for req_key, req_val in request.items():
            if not isinstance(req_key, str):
                raise TypeError("Request keys must be strings")
            if not isinstance(req_val, (int, float)) or isinstance(req_val, bool):
                raise TypeError("Request values must be numbers")
            if req_val < 0 or math.isnan(req_val) or math.isinf(req_val):
                raise ValueError("Request values must be non-negative finite numbers")
            if req_key not in resources:
                return False  # requested resource does not exist

            total_used[req_key] += req_val
            if total_used[req_key] > resources[req_key]:
                return False  # exceeds available capacity

    # At least one resource must remain (partly) unallocated
    return any(used < resources[resource] for resource, used in total_used.items())
