from typing import Dict, List, Union
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests can be satisfied given limited capacities.

    The allocation is feasible if, for every resource, the total amount
    requested across all requests does not exceed that resource's capacity.
    A request for a resource that does not exist is only satisfiable if the
    amount requested is zero.

    Raises:
        TypeError: If input types are incorrect.
        ValueError: If numeric values are invalid (negative, NaN, or infinite).

    Returns:
        True if every request can be satisfied, False otherwise.
    """
    if not isinstance(resources, dict):
        raise TypeError("resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("requests must be a list")

    for r_key, r_val in resources.items():
        if not isinstance(r_key, str):
            raise TypeError(f"resource key must be a string, got {type(r_key)}")
        if not isinstance(r_val, (int, float)):
            raise TypeError(f"resource value must be numeric, got {type(r_val)}")
        if r_val < 0 or math.isnan(r_val) or math.isinf(r_val):
            raise ValueError(f"resource value must be non-negative finite number, got {r_val}")

    total_demand: Dict[str, Number] = {}

    for req in requests:
        if not isinstance(req, dict):
            raise TypeError("each request must be a dictionary")
        for req_key, req_val in req.items():
            if not isinstance(req_key, str):
                raise TypeError(f"request key must be a string, got {type(req_key)}")
            if not isinstance(req_val, (int, float)):
                raise TypeError(f"request value must be numeric, got {type(req_val)}")
            if req_val < 0 or math.isnan(req_val) or math.isinf(req_val):
                raise ValueError(f"request value must be non-negative finite number, got {req_val}")
            total_demand[req_key] = total_demand.get(req_key, 0) + req_val

    for r_name, demand in total_demand.items():
        if demand > resources.get(r_name, 0):
            return False

    return True
