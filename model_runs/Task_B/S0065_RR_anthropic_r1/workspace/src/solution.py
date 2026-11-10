from typing import Dict, List, Union
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, int]]
) -> bool:
    """
    Determines if a set of resource requests can be satisfied given available resources,
    ensuring at least one resource remains unallocated.

    Args:
        resources (Dict[str, Number]): Available resources as {resource_name: amount}.
        requests (List[Dict[str, int]]): List of requests as {resource_name: amount}.

    Returns:
        bool: True if all requests fit and not all resources are fully consumed, else False.
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
                raise TypeError("Request keys must be strings.")
            if res not in resources:
                raise ValueError(f"Resource '{res}' not defined in resources.")
            if isinstance(amount, bool) or not isinstance(amount, int):
                raise TypeError("Requested amount must be an integer.")
            if amount <= 0:
                raise ValueError("Requested amounts must be positive.")

    # --- Track allocation ---
    allocation = {res: 0 for res in resources}

    for req in requests:
        for res, amount in req.items():
            allocation[res] += amount
            if allocation[res] > resources[res]:
                return False  # exceeds available resource

    # --- Enforce "at least one resource must remain unallocated" ---
    if all(allocation[res] >= resources[res] for res in resources):
        return False

    return True
