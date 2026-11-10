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

    Raises:
        ValueError: If the inputs are not in the expected data structures/format.

    Args:
        resources : Dict[str, Number], Mapping from resource name to total available capacity.
        requests : List[Dict[str, Number]], List of requests. Each request is a mapping from resource name to the amount required.

    Returns:
        True if all requests can be satisfied without exceeding any capacity
        (including an empty request list); False if a request refers to a
        nonexistent resource, is invalid, or total demand exceeds capacity.
    """

    # --- Format checks ---
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
            # Invalid request: unknown resource, or non-finite / negative amount
            if key not in resources:
                return False
            if math.isnan(value) or math.isinf(value) or value < 0:
                return False

            usage[key] = usage.get(key, 0) + value
            if usage[key] > resources[key]:
                return False

    return True
