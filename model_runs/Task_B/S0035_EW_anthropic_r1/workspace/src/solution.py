from typing import Dict, List, Union
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Args:
        resources: Dictionary mapping resource names (str) to available capacities (int/float).
        requests: List of dictionaries, each mapping resource names to requested amounts (int/float).

    Returns:
        True if all requests can be fulfilled with the available resources (consuming
        all of a resource is allowed); False if a requested resource does not exist
        or its capacity is insufficient.

    Raises:
        TypeError: If resources/requests are not proper types, or keys/values are wrong type.
        ValueError: If numeric values are invalid (negative, NaN, Inf).
    """

    # --- Type checks ---
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    # --- Validate resources ---
    for r_key, r_value in resources.items():
        if not isinstance(r_key, str):
            raise TypeError(f"Resource key must be a string: {r_key}")
        if not isinstance(r_value, (int, float)):
            raise TypeError(f"Resource value must be numeric for '{r_key}': {r_value}")
        if r_value < 0 or math.isnan(r_value) or math.isinf(r_value):
            raise ValueError(f"Invalid numeric value for resource '{r_key}': {r_value}")

    total_requested: Dict[str, Number] = {}
    feasible = True

    # --- Validate requests and accumulate demand ---
    for req in requests:
        if not isinstance(req, dict):
            raise TypeError("Each request must be a dictionary")
        for req_key, req_value in req.items():
            if not isinstance(req_key, str):
                raise TypeError(f"Request key must be string: {req_key}")
            if not isinstance(req_value, (int, float)):
                raise TypeError(f"Request value must be numeric for '{req_key}': {req_value}")
            if req_value < 0 or math.isnan(req_value) or math.isinf(req_value):
                raise ValueError(f"Invalid numeric value in request for '{req_key}': {req_value}")
            if req_key not in resources:
                feasible = False  # resource does not exist
                continue

            total_requested[req_key] = total_requested.get(req_key, 0) + req_value
            if total_requested[req_key] > resources[req_key]:
                feasible = False

    return feasible
