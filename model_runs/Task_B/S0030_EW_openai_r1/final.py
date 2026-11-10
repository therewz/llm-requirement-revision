from typing import Dict, List, Union
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Constraints:
      - All resource capacities are finite non-negative numbers.
      - Requests must reference only valid resources.
      - Request amounts must be finite, non-negative numbers.

    Returns:
        True if all requests can be satisfied, including exact-capacity allocations.
        False if a resource is undefined or any total exceeds its capacity.

    Raises:
        TypeError: If input types are invalid (not dict/list, keys not strings, values not numbers)
        ValueError: If numeric values are negative or non-finite.
    """
    # ---- Type checks ----
    if not isinstance(resources, dict):
        raise TypeError("resources must be a dict")
    if not isinstance(requests, list):
        raise TypeError("requests must be a list")

    # ---- Validate resources ----
    for name, cap in resources.items():
        if not isinstance(name, str):
            raise TypeError("resource names must be strings")
        if not isinstance(cap, (int, float)):
            raise TypeError("resource capacities must be numeric")
        if isinstance(cap, float) and not math.isfinite(cap):
            raise ValueError("resource capacities must be finite")
        if cap < 0:
            raise ValueError("resource capacities must be non-negative")

    used: Dict[str, Number] = {k: 0 for k in resources}
    has_unknown_resource = False

    # ---- Process and validate all requests ----
    for req in requests:
        if not isinstance(req, dict):
            raise TypeError("each request must be a dict")
        for rname, amount in req.items():
            if not isinstance(rname, str):
                raise TypeError("request resource names must be strings")
            if not isinstance(amount, (int, float)):
                raise TypeError("request amounts must be numeric")
            if isinstance(amount, float) and not math.isfinite(amount):
                raise ValueError("request amounts must be finite")
            if amount < 0:
                raise ValueError("request amounts must be non-negative")
            if rname not in resources:
                has_unknown_resource = True
            else:
                used[rname] += amount

    # ---- Check capacity constraints ----
    if has_unknown_resource:
        return False
    for rname, cap in resources.items():
        if used[rname] > cap:
            return False

    return True
