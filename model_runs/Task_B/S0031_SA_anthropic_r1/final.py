from typing import Dict, List, Union
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine if a set of resource requests can be satisfied given available resources.

    Returns True if the total requested amount of every resource does not exceed
    its capacity (no requests is trivially feasible), otherwise False.

    Raises:
        TypeError: for invalid types
        ValueError: for invalid numeric values or unknown resources
    """

    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    for key, cap in resources.items():
        if not isinstance(key, str):
            raise TypeError(f"Resource key must be a string, got {type(key)}")
        if not isinstance(cap, (int, float)):
            raise TypeError(f"Resource '{key}' value must be a number")
        if math.isnan(cap) or math.isinf(cap) or cap < 0:
            raise ValueError(f"Resource '{key}' has invalid numeric value")

    usage = {r: 0 for r in resources}

    for req in requests:
        if not isinstance(req, dict):
            raise TypeError("Each request must be a dictionary")
        for r_key, amount in req.items():
            if not isinstance(r_key, str):
                raise TypeError(f"Request key must be a string, got {type(r_key)}")
            if r_key not in resources:
                raise ValueError(f"Request contains unknown resource '{r_key}'")
            if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                raise TypeError(f"Request value must be a number, got {type(amount)}")
            if math.isnan(amount) or math.isinf(amount) or amount < 0:
                raise ValueError(f"Request for '{r_key}' has invalid numeric value")

            usage[r_key] += amount
            if usage[r_key] > resources[r_key]:
                return False  # Over allocation

    return True
