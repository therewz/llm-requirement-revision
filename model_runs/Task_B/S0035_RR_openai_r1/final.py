from typing import Dict, List, Union
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests fit within the available resource capacities.

    Args:
        resources: Dictionary mapping resource names to available capacities.
        requests: List of dictionaries mapping resource names to requested amounts.

    Returns:
        True if all requests can be satisfied and some capacity remains unused.
        False if a requested resource is missing, a capacity is exceeded, or no
        capacity would remain unallocated (including when resources is empty).

    Raises:
        TypeError: If resources/requests or their keys/values have incorrect types.
        ValueError: If numeric values are negative, NaN, or infinite.
    """
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    for r_key, r_value in resources.items():
        if not isinstance(r_key, str):
            raise TypeError(f"Resource key must be a string: {r_key}")
        if not isinstance(r_value, (int, float)):
            raise TypeError(f"Resource value must be numeric for '{r_key}': {r_value}")
        if r_value < 0 or (isinstance(r_value, float) and not math.isfinite(r_value)):
            raise ValueError(f"Invalid numeric value for resource '{r_key}': {r_value}")

    total_requested: Dict[str, Number] = {}

    for req in requests:
        if not isinstance(req, dict):
            raise TypeError("Each request must be a dictionary")
        for req_key, req_value in req.items():
            if not isinstance(req_key, str):
                raise TypeError(f"Request key must be string: {req_key}")
            if not isinstance(req_value, (int, float)):
                raise TypeError(f"Request value must be numeric for '{req_key}': {req_value}")
            if req_value < 0 or (isinstance(req_value, float) and not math.isfinite(req_value)):
                raise ValueError(f"Invalid numeric value in request for '{req_key}': {req_value}")
            if req_key not in resources:
                return False

            total_requested[req_key] = total_requested.get(req_key, 0) + req_value
            if total_requested[req_key] > resources[req_key]:
                return False

    return any(
        total_requested.get(resource, 0) < capacity
        for resource, capacity in resources.items()
    )
