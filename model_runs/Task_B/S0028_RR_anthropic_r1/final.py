from typing import Dict, List, Union, Any
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    # -----------------------
    # Input Type Validations
    # -----------------------
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    # Validate resources dict keys and values
    for r_key, r_value in resources.items():
        if not isinstance(r_key, str):
            raise TypeError(f"Resource key must be string, got {type(r_key)}")
        if not isinstance(r_value, (int, float)):
            raise TypeError(f"Resource value must be a number, got {type(r_value)}")
        if r_value < 0 or math.isnan(r_value) or math.isinf(r_value):
            raise ValueError(f"Resource value invalid: {r_value}")

    # Validate each request in requests
    for req in requests:
        if not isinstance(req, dict):
            raise TypeError(f"Each request must be a dictionary, got {type(req)}")
        for r_key, r_value in req.items():
            if not isinstance(r_key, str):
                raise TypeError(f"Request key must be string, got {type(r_key)}")
            if not isinstance(r_value, (int, float)):
                raise TypeError(f"Request value must be a number, got {type(r_value)}")
            if r_value < 0 or math.isnan(r_value) or math.isinf(r_value):
                raise ValueError(f"Request value invalid: {r_value}")
            if r_key not in resources:
                raise ValueError(f"Request references unknown resource: {r_key}")

    # -----------------------
    # Allocation Logic
    # -----------------------
    total_request = {r: 0 for r in resources}

    for req in requests:
        for r_type, amount in req.items():
            total_request[r_type] += amount

    # Every request must be fully satisfied: no type may exceed capacity
    for r_type, total in total_request.items():
        if total > resources[r_type]:
            return False

    # At least one resource must remain unallocated after assignment
    return any(total_request[r_type] < resources[r_type] for r_type in resources)
