from typing import Dict, List, Union
from numbers import Number as Numeric

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether requests fit within independent resource capacities,
    with some available capacity remaining after allocation.

    Args:
        resources: Mapping from resource name to total available capacity.
        requests: List of dictionaries mapping resource names to required amounts.

    Returns:
        True if no resource is over capacity and at least one has capacity left.
        Missing requested resources make the allocation infeasible.

    Raises:
        TypeError: If containers, resource names, or numeric values have invalid types.
        ValueError: If a request is not a dictionary or a value is not non-negative.
    """
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list.")

    # Validate all inputs before deciding whether the allocation is feasible.
    for key, value in resources.items():
        if not isinstance(key, str):
            raise TypeError("Resource keys must be strings.")
        if not isinstance(value, Numeric):
            raise TypeError(f"Resource value for '{key}' must be a number.")
        if not value >= 0:
            raise ValueError(f"Resource value for '{key}' must be non-negative.")

    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Each request must be a dictionary.")
        for key, value in request.items():
            if not isinstance(key, str):
                raise TypeError("Request keys must be strings.")
            if not isinstance(value, Numeric):
                raise TypeError(f"Request value for '{key}' must be a number.")
            if not value >= 0:
                raise ValueError(f"Request value for '{key}' must be non-negative.")

    total_demand = {key: 0 for key in resources}
    for request in requests:
        for key, value in request.items():
            if key not in resources:
                return False
            total_demand[key] += value

    for key, demand in total_demand.items():
        if demand > resources[key]:
            return False

    # Empty or fully consumed resources cannot leave any capacity unallocated.
    return any(total_demand[key] < capacity for key, capacity in resources.items())
