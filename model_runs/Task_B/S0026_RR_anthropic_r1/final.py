from typing import Dict, List, Union
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities,
    with the constraint that at least one resource must remain unallocated
    (i.e. have remaining capacity > 0) after assignment.

    Only total demand per resource is checked, so request order is irrelevant.
    Resource names are case-sensitive. Demand for a resource that is not listed
    in `resources` is not checked against any capacity. Inputs are not modified.

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
        if math.isnan(r_value) or math.isinf(r_value) or r_value < 0:
            raise ValueError("Resource values must be non-negative, finite numbers")

    for request in requests:
        if not isinstance(request, dict):
            raise TypeError("Each request must be a dictionary")
        for req_key, req_value in request.items():
            if not isinstance(req_key, str):
                raise TypeError("Request keys must be strings")
            if not isinstance(req_value, (int, float)):
                raise TypeError("Request values must be numbers")
            if math.isnan(req_value) or math.isinf(req_value) or req_value < 0:
                raise ValueError("Request values must be non-negative, finite numbers")

    # Total demand per resource
    total_demand = {}
    for request in requests:
        for r_key, r_value in request.items():
            total_demand[r_key] = total_demand.get(r_key, 0) + r_value

    # No resource may be over-allocated
    for r_key, r_capacity in resources.items():
        if total_demand.get(r_key, 0) > r_capacity:
            return False

    # At least one resource must remain unallocated
    return any(total_demand.get(r_key, 0) < r_capacity
               for r_key, r_capacity in resources.items())
