from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether total resource requests fit within the available capacities.

    Capacities and request amounts must be non-negative numbers. Each request
    must be a dictionary. Empty requests are valid, and capacities may be used
    in full.

    Returns:
        True if every requested resource is defined and no total exceeds its
        capacity; False otherwise.

    Raises:
        TypeError: If input types are invalid (not dict/list, keys not strings,
            values not numbers).
        ValueError: If a capacity or request amount is negative.
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
        if cap < 0:
            raise ValueError("resource capacities must be non-negative")

    used: Dict[str, Number] = {k: 0 for k in resources}
    feasible = True

    # ---- Process and validate all requests, even if allocation is infeasible ----
    for req in requests:
        if not isinstance(req, dict):
            raise TypeError("each request must be a dict")
        for rname, amount in req.items():
            if not isinstance(rname, str):
                raise TypeError("request resource names must be strings")
            if not isinstance(amount, (int, float)):
                raise TypeError("request amounts must be numeric")
            if amount < 0:
                raise ValueError("request amounts must be non-negative")
            if rname not in resources:
                feasible = False
            else:
                used[rname] += amount

    # ---- Check capacity constraints ----
    for rname, cap in resources.items():
        if used[rname] > cap:
            feasible = False

    return feasible
