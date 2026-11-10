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
        resources : Dict[str, Number], Mapping from resource name (e.g. "cpu", "ram", "mem")
                    to total available capacity.
        requests : List[Dict[str, Number]], List of requests. Each request is a mapping from
                   resource name to the amount required.

    Returns:
        True if all requests can be satisfied (total demand per resource does not exceed
        its capacity; an empty request list is feasible). False if any request is invalid
        (unknown resource, negative or non-finite amount) or total demand for a resource
        exceeds its capacity.

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

    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Each request must be a dictionary")
        for key, value in request.items():
            if not isinstance(key, str):
                raise ValueError("Request keys must be strings")
            if not _is_number(value):
                raise ValueError("Request values must be numbers")

    # --- Feasibility ---
    usage: Dict[str, Number] = {}

    for request in requests:
        for key, value in request.items():
            if key not in resources:
                return False
            if math.isnan(value) or math.isinf(value) or value < 0:
                return False
            usage.setdefault(key, []).append(value)

    for key, amounts in usage.items():
        capacity = resources[key]
        if math.isnan(capacity) or capacity < 0:
            return False
        total = math.fsum(amounts)
        if total > capacity and not math.isclose(total, capacity, rel_tol=1e-9, abs_tol=1e-12):
            return False

    return True
