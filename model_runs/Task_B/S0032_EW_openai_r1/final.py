from fractions import Fraction
from typing import Dict, List, Union
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether resource requests fit within the available capacities.

    Args:
        resources: Dictionary of available resources with their maximum capacities.
        requests: List of dictionaries where each dictionary represents a resource request.

    Returns:
        True if every requested resource exists and its total non-negative demand
        does not exceed its capacity, False otherwise. Full utilization is valid.

    Raises:
        TypeError: For invalid input types.
    """

    # Validate resources
    if resources is None:
        raise TypeError("Resources cannot be None")
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")

    for key, value in resources.items():
        if not isinstance(key, str):
            raise TypeError("Resource keys must be strings")
        if not isinstance(value, (int, float)):
            raise TypeError("Resource values must be numbers")
        if not value >= 0:
            return False

    # Validate requests
    if requests is None:
        raise TypeError("Requests cannot be None")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    used: Dict[str, Fraction] = {resource: Fraction(0) for resource in resources}

    for request in requests:
        if not isinstance(request, dict):
            raise TypeError("Each request must be a dictionary")

        for key, value in request.items():
            if not isinstance(key, str):
                raise TypeError("Request keys must be strings")
            if key not in resources:
                return False
            if not isinstance(value, (int, float)):
                raise TypeError("Request values must be numbers")
            if not value >= 0:
                return False

            capacity = resources[key]
            if value > capacity:
                return False
            if capacity == math.inf:
                continue

            # Exact accumulation keeps the result independent of request order.
            used[key] += Fraction(value)
            if used[key] > capacity:
                return False

    return True
