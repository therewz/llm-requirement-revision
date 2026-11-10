from typing import Dict, List, Union
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine if a set of resource requests can be satisfied given available resources,
    with the requirement that at least one resource must remain unallocated.

    Raises:
        TypeError: for invalid types
        ValueError: for invalid numeric values
    """

    # Type validation
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

    # Track usage
    usage = {r: 0 for r in resources}

    for req in requests:
        if not isinstance(req, dict):
            raise TypeError("Each request must be a dictionary")
        for r_key, amount in req.items():
            if not isinstance(r_key, str):
                raise TypeError(f"Request key must be a string, got {type(r_key)}")
            if r_key not in resources:
                raise ValueError(f"Request contains unknown resource '{r_key}'")
            if not isinstance(amount, (int, float)):
                raise TypeError(f"Request value must be a number, got {type(amount)}")
            if isinstance(amount, bool) or math.isnan(amount) or math.isinf(amount) or amount < 0:
                raise ValueError(f"Request for '{r_key}' has invalid numeric value")

            usage[r_key] += amount
            if usage[r_key] > resources[r_key]:
                return False  # Over allocation

    # At least one resource must have leftover capacity after assignment
    for r, cap in resources.items():
        if usage[r] < cap:
            return True

    return False  # All resources fully consumed (or no resources at all)
