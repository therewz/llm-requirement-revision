from typing import Dict, List
import math


def is_allocation_feasible(
    resources: Dict[str, int],
    requests: List[Dict[str, int]]
) -> bool:
    """
    Determines if a list of resource requests can be satisfied given resource capacities.

    Args:
        resources: Available capacity as {resource_name: amount}.
        requests: List of requests, each a dict {resource_name: amount}.

    Returns:
        True if the total requested amount of every resource does not exceed
        its capacity, else False.

    Raises:
        TypeError / ValueError for malformed input (wrong types, undeclared
        resources, non-integer or non-positive amounts).
    """

    # --- Input type checks ---
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list of dictionaries.")

    # --- Validate resources ---
    for res, amount in resources.items():
        if not isinstance(res, str):
            raise TypeError("Resource keys must be strings.")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Resource amounts must be numeric.")
        if math.isnan(amount) or math.isinf(amount):
            raise ValueError("Resource amounts cannot be NaN or infinite.")
        if amount < 0:
            raise ValueError("Resource amounts cannot be negative.")

    # --- Validate requests ---
    for req in requests:
        if not isinstance(req, dict):
            raise TypeError("Each request must be a dictionary.")
        for res, amount in req.items():
            if not isinstance(res, str):
                raise TypeError("Request resource names must be strings.")
            if res not in resources:
                raise ValueError(f"Resource '{res}' not defined in resources.")
            if isinstance(amount, bool) or not isinstance(amount, int):
                raise TypeError("Requested amount must be an integer.")
            if amount <= 0:
                raise ValueError("Requested amount must be positive.")

    # --- Track allocation ---
    allocation = {res: 0 for res in resources}
    for req in requests:
        for res, amount in req.items():
            allocation[res] += amount
            if allocation[res] > resources[res]:
                return False

    return True
