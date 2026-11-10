from typing import Dict, List, Union
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determines if a set of resource requests can be satisfied cumulatively
    given the available resource capacities. Inputs are not modified.
    """

    # Validate top-level structures
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list.")

    # Validate resources
    for key, value in resources.items():
        if not isinstance(key, str):
            raise TypeError("Resource keys must be strings.")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Resource values must be numeric.")
        if math.isnan(value) or math.isinf(value):
            raise ValueError("Resource values must be finite numbers.")
        if value < 0:
            raise ValueError("Resource capacities cannot be negative.")

    # Validate all requests first
    for req_idx, req in enumerate(requests):
        if not isinstance(req, dict):
            raise TypeError(f"Request at index {req_idx} must be a dictionary.")
        for key, value in req.items():
            if not isinstance(key, str):
                raise TypeError("Request keys must be strings.")
            if key not in resources:
                raise ValueError(f"Request contains unknown resource '{key}'.")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("Request values must be numeric.")
            if math.isnan(value) or math.isinf(value):
                raise ValueError("Request values must be finite numbers.")
            if value < 0:
                raise ValueError("Request values cannot be negative.")

    # Cumulative allocation on a copy (inputs stay unchanged)
    remaining = dict(resources)
    for req in requests:
        for key, value in req.items():
            if value > remaining[key]:
                return False
            remaining[key] -= value

    return True
