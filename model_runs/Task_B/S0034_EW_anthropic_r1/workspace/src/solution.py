from typing import Dict, List, Union
import math

Number = Union[int, float]


def _check_number(value, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a number.")
    if value < 0 or math.isnan(value) or math.isinf(value):
        raise ValueError(f"{label} must be non-negative, finite, and valid.")


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Args:
        resources: Mapping from resource name to total available capacity.
        requests: List of requests. Each request is a mapping from resource name
            to the amount required.

    Returns:
        True if total demand for every resource is within its capacity, False otherwise
        (including when a request names a resource that is not available).

    Raises:
        ValueError: If a request is not a dictionary, or numeric values are negative/NaN/Inf.
        TypeError: If other inputs are not of the expected type.
    """
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list.")

    for key, value in resources.items():
        if not isinstance(key, str):
            raise TypeError("Resource keys must be strings.")
        _check_number(value, f"Resource value for '{key}'")

    missing_resource = False
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Each request must be a dictionary.")
        for key, value in request.items():
            if not isinstance(key, str):
                raise TypeError("Request keys must be strings.")
            _check_number(value, f"Request value for '{key}'")
            if key not in resources:
                missing_resource = True

    if missing_resource:
        return False

    total_demand = {key: 0 for key in resources}
    for request in requests:
        for key, value in request.items():
            total_demand[key] += value

    for key, demand in total_demand.items():
        if demand > resources[key]:
            return False

    return True
