from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether resource requests can be satisfied within available capacities.

    Args:
        resources: Mapping from resource name to total available capacity.
        requests: List of mappings from resource name to the amount required.

    Returns:
        True if every requested resource exists and total demand does not exceed
        its capacity, including when all available capacity is used.

    Raises:
        TypeError: If input containers, keys, or numeric values have invalid types.
        ValueError: If a request is not a dictionary or a numeric value is not
            non-negative.
    """
    # Basic type checks
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list.")

    # Validate resources
    for key, value in resources.items():
        if not isinstance(key, str):
            raise TypeError("Resource keys must be strings.")
        if not isinstance(value, (int, float)):
            raise TypeError(f"Resource value for '{key}' must be a number.")
        if not value >= 0:
            raise ValueError(f"Resource value for '{key}' must be non-negative.")

    # Validate all requests before checking feasibility.
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Each request must be a dictionary.")
        for key, value in request.items():
            if not isinstance(key, str):
                raise TypeError("Request keys must be strings.")
            if not isinstance(value, (int, float)):
                raise TypeError(f"Request value for '{key}' must be a number.")
            if not value >= 0:
                raise ValueError(f"Request value for '{key}' must be non-negative.")

    # Calculate total demand, rejecting requests for unavailable resources.
    total_demand = {key: 0 for key in resources}
    for request in requests:
        for key, value in request.items():
            if key not in resources:
                return False
            total_demand[key] += value

    return all(demand <= resources[key] for key, demand in total_demand.items())
