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
        resources: Dictionary of available resources with their maximum capacities.
        requests: List of dictionaries where each dictionary represents a resource request.

    Returns:
        True if a valid allocation exists, False otherwise (including when a request
        references an unknown resource, has a negative/invalid amount, or no resources
        are available).

    Raises:
        TypeError: For invalid types of inputs.
    """

    # Validate resources
    if resources is None:
        raise TypeError("Resources cannot be None")
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not resources:
        return False

    for key, value in resources.items():
        if not isinstance(key, str):
            raise TypeError("Resource keys must be strings")
        if not isinstance(value, (int, float)):
            raise TypeError("Resource values must be numbers")
        if value < 0 or math.isnan(value) or math.isinf(value):
            return False

    # Validate requests
    if requests is None:
        raise TypeError("Requests cannot be None")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    used: Dict[str, Number] = {resource: 0 for resource in resources}

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
            if value < 0 or math.isnan(value) or math.isinf(value):
                return False

            # Accumulate used resources
            used[key] += value
            if used[key] > resources[key]:
                return False

    return True
