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
    Determine whether a set of resource requests can be satisfied given limited capacities,
    while leaving at least one resource not fully allocated.

    Args:
        resources: Mapping from resource name to total available capacity.
        requests: List of requests. Each request maps resource name to amount required.

    Returns:
        True if every request is valid, no resource's total requested amount exceeds its
        capacity, and at least one resource remains (partly) unallocated.
        False if a request is invalid (unknown resource, negative/non-finite amount),
        a capacity is exceeded, or all resources would be completely consumed.

    Raises:
        ValueError: If the inputs are not in the expected data structures.
    """

    # --- Format checks (ValueError) ---
    if not isinstance(resources, dict):
        raise ValueError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise ValueError("Requests must be a list")

    for key, value in resources.items():
        if not isinstance(key, str):
            raise ValueError("Resource keys must be strings")
        if not _is_number(value):
            raise ValueError("Resource values must be numbers")
        if math.isnan(value) or math.isinf(value) or value < 0:
            raise ValueError("Resource values must be non-negative, finite numbers")

    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Each request must be a dictionary")
        for key, value in request.items():
            if not isinstance(key, str):
                raise ValueError("Request keys must be strings")
            if not _is_number(value):
                raise ValueError("Request values must be numbers")

    # --- Feasibility checks ---
    usage: Dict[str, Number] = {}

    for request in requests:
        for key, value in request.items():
            # Invalid request: unknown resource or invalid amount
            if key not in resources:
                return False
            if math.isnan(value) or math.isinf(value) or value < 0:
                return False
            usage[key] = usage.get(key, 0) + value
            if usage[key] > resources[key]:
                return False

    # At least one resource must remain unallocated
    for resource, capacity in resources.items():
        if usage.get(resource, 0) < capacity:
            return True

    return False
