from typing import Dict, List, Union
import math

Number = Union[int, float]


def _check_number(value, label):
    if not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a number.")
    if math.isnan(value) or value < 0:
        raise ValueError(f"{label} must be non-negative and valid.")


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
        (including when a request asks for a resource that is not available).

    Raises:
        ValueError: If a request is not a dict, or numeric values are negative/NaN.
        TypeError: If resources/requests have the wrong container type or values are not numeric.
    """
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list.")

    for key, value in resources.items():
        _check_number(value, f"Resource value for '{key}'")

    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Each request must be a dictionary.")
        for key, value in request.items():
            _check_number(value, f"Request value for '{key}'")

    total_demand = {}
    for request in requests:
        for key, value in request.items():
            total_demand[key] = total_demand.get(key, 0) + value

    for key, demand in total_demand.items():
        if key not in resources:
            return False
        if demand > resources[key]:
            return False

    return True
