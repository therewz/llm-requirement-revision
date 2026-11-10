from typing import Dict, List, Union
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Returns:
        True if the total requested amount of every resource is within its capacity
        (an empty request list is feasible). False if any resource's capacity is
        exceeded or a request references an undefined resource.

    Raises:
        TypeError: If input types are invalid (not dict/list, request not a dict,
            keys not strings, values not numbers)
        ValueError: If numeric values are negative or non-finite.
    """
    EPS = 1e-9  # tolerance for float comparisons

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
        if not math.isfinite(float(cap)):
            raise ValueError("resource capacities must be finite")
        if float(cap) < 0:
            raise ValueError("resource capacities must be non-negative")

    used: Dict[str, float] = {k: 0.0 for k in resources}
    unknown_resource = False

    # ---- Process requests (all are validated) ----
    for req in requests:
        if not isinstance(req, dict):
            raise TypeError("each request must be a dict")
        for rname, amount in req.items():
            if not isinstance(rname, str):
                raise TypeError("request resource names must be strings")
            if not isinstance(amount, (int, float)):
                raise TypeError("request amounts must be numeric")
            if not math.isfinite(float(amount)):
                raise ValueError("request amounts must be finite")
            if float(amount) < 0:
                raise ValueError("request amounts must be non-negative")
            if rname not in resources:
                unknown_resource = True
            else:
                used[rname] += float(amount)

    if unknown_resource:
        return False

    # ---- Check capacity constraints ----
    for rname, cap in resources.items():
        if used[rname] > float(cap) + EPS:
            return False

    return True
