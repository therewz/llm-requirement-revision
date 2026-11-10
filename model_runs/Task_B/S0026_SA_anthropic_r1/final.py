from typing import Dict, List, Union
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether the total demand of all requests fits within the available
    resources. Resource names are case-sensitive. Only total demand per resource
    is checked, so request order is irrelevant. Requests naming a resource that
    is not available are not counted against any capacity. An empty request list
    is feasible. Inputs are not modified.

    Raises:
        TypeError: If inputs are of wrong type.
        ValueError: If numeric values are invalid (negative, NaN, or infinite).
    """
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    for r_key, r_value in resources.items():
        if not isinstance(r_key, str):
            raise TypeError("Resource keys must be strings")
        if not isinstance(r_value, (int, float)):
            raise TypeError("Resource values must be numbers")
        if r_value < 0 or math.isnan(r_value) or math.isinf(r_value):
            raise ValueError("Resource values must be non-negative, finite numbers")

    for request in requests:
        if not isinstance(request, dict):
            raise TypeError("Each request must be a dictionary")
        for req_key, req_value in request.items():
            if not isinstance(req_key, str):
                raise TypeError("Request keys must be strings")
            if not isinstance(req_value, (int, float)):
                raise TypeError("Request values must be numbers")
            if req_value < 0 or math.isnan(req_value) or math.isinf(req_value):
                raise ValueError("Request values must be non-negative, finite numbers")

    total_demand = {}
    for request in requests:
        for r_key, r_value in request.items():
            total_demand[r_key] = total_demand.get(r_key, 0) + r_value

    for r_key, r_capacity in resources.items():
        if total_demand.get(r_key, 0) > r_capacity:
            return False

    return True
