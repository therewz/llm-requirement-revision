from typing import Dict, List, Union
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine if a list of resource requests is feasible given available resources.
    An allocation is feasible iff, for every resource, the total requested
    quantity is less than or equal to the available amount.

    Args:
        resources: Mapping of resource names to available capacity (non-negative numbers).
        requests: List of request dictionaries, each mapping resource names to requested quantities.

    Returns:
        True if the total requested quantity of every resource <= available amount, else False.

    Raises:
        TypeError: if types of inputs are invalid.
        ValueError: if values are negative, NaN, infinite, or reference missing resources.
    """

    # --- Type checks for inputs ---
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    # --- Validate resources ---
    for res, qty in resources.items():
        if not isinstance(res, str):
            raise TypeError(f"Resource key '{res}' must be a string")
        if isinstance(qty, bool) or not isinstance(qty, (int, float)):
            raise TypeError(f"Resource '{res}' must be numeric, not {type(qty).__name__}")
        if qty < 0 or math.isnan(qty) or math.isinf(qty):
            raise ValueError(f"Resource '{res}' must be non-negative, finite, and not NaN")

    # --- Initialize total demand dictionary ---
    total_demand: Dict[str, Number] = {res: 0 for res in resources}

    # --- Sum up all requests ---
    for i, request in enumerate(requests):
        if not isinstance(request, dict):
            raise TypeError(f"Request at index {i} must be a dictionary")
        for res, qty in request.items():
            if not isinstance(res, str):
                raise TypeError(f"Request key '{res}' must be a string")
            if res not in resources:
                raise ValueError(f"Request asks for unknown resource '{res}'")
            if isinstance(qty, bool) or not isinstance(qty, (int, float)):
                raise TypeError(f"Request quantity for '{res}' must be numeric, not {type(qty).__name__}")
            if qty < 0 or math.isnan(qty) or math.isinf(qty):
                raise ValueError(f"Request quantity for '{res}' must be non-negative, finite, and not NaN")
            total_demand[res] += qty

    # --- Feasible iff every resource's total demand <= availability ---
    for res, demand in total_demand.items():
        if demand > resources[res]:
            return False

    return True
