from typing import Dict, List, Union
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests fit cumulatively within the available
    capacities, without modifying either input.
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
        if isinstance(value, bool):
            raise TypeError("Resource values cannot be boolean.")
        if not isinstance(value, (int, float)):
            raise TypeError("Resource values must be numeric.")
        if isinstance(value, float) and math.isnan(value):
            raise ValueError("Resource values cannot be NaN.")
        if value < 0:
            raise ValueError("Resource capacities cannot be negative.")

    remaining = resources.copy()

    # Validate and process requests
    for req_idx, req in enumerate(requests):
        if not isinstance(req, dict):
            raise TypeError(f"Request at index {req_idx} must be a dictionary.")
        for key, value in req.items():
            if not isinstance(key, str):
                raise TypeError("Request keys must be strings.")
            if key not in resources:
                raise ValueError(f"Request contains unknown resource '{key}'.")
            if isinstance(value, bool):
                raise TypeError("Request values cannot be boolean.")
            if not isinstance(value, (int, float)):
                raise TypeError("Request values must be numeric.")
            if isinstance(value, float) and math.isnan(value):
                raise ValueError("Request values cannot be NaN.")
            if value < 0:
                raise ValueError("Request values cannot be negative.")
            if value > remaining[key]:
                return False
            # An unbounded capacity stays unbounded, including after an
            # infinite request; avoid turning infinity - infinity into NaN.
            if remaining[key] != math.inf:
                remaining[key] -= value

    return True
