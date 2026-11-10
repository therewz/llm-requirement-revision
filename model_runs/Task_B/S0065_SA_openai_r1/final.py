from typing import Dict, List, Union

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests fit within the available resource inventory.

    Resource names must be strings and amounts must be integers. Inventory
    amounts must be nonnegative, and requested amounts must be positive.
    Invalid inputs raise TypeError or ValueError.

    Args:
        resources (Dict[str, Number]): Available resources as {resource_name: amount}.
        requests (List[Dict[str, Number]]): List of requests as {resource_name: amount}.

    Returns:
        bool: True if cumulative requests do not exceed any resource's capacity.
    """

    # --- Input type checks ---
    if resources is None:
        raise TypeError("Resources cannot be None.")
    if requests is None:
        raise TypeError("Requests cannot be None.")
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list of dictionaries.")

    # --- Validate resources ---
    for res, amount in resources.items():
        if not isinstance(res, str):
            raise TypeError("Resource keys must be strings.")
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise TypeError("Resource amounts must be integers.")
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
            if not isinstance(amount, int) or isinstance(amount, bool):
                raise TypeError("Requested amounts must be integers.")
            if amount <= 0:
                raise ValueError("Requested amounts must be positive.")

    # --- Track allocation ---
    allocation = {res: 0 for res in resources}

    for req in requests:
        for res, amount in req.items():
            allocation[res] += amount
            if allocation[res] > resources[res]:
                return False

    return True
