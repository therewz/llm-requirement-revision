from typing import Dict, List, Union, Any
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    # Accept the arguments in either order (requests, resources) or
    # (resources, requests); the types make the intent unambiguous.
    if isinstance(resources, list) and isinstance(requests, dict):
        resources, requests = requests, resources

    # -----------------------
    # Input Type Validations
    # -----------------------
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    for r_key, r_value in resources.items():
        if not isinstance(r_key, str):
            raise TypeError(f"Resource key must be string, got {type(r_key)}")
        if not isinstance(r_value, (int, float)):
            raise TypeError(f"Resource value must be a number, got {type(r_value)}")
        if r_value < 0 or math.isnan(r_value) or math.isinf(r_value):
            raise ValueError(f"Resource value invalid: {r_value}")

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
    # Allocation Logic (no mutation of inputs)
    # -----------------------
    total_request = {r: 0 for r in resources}
    for req in requests:
        for r_type, amount in req.items():
            total_request[r_type] += amount

    # Feasible when every resource's total demand fits within its capacity
    # (exactly meeting capacity is allowed).
    return all(total_request[r] <= resources[r] for r in resources)
