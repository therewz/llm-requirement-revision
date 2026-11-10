from typing import Dict, List, Union

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests fit while leaving some capacity unallocated.

    Resource capacities and requested amounts must be non-negative numbers.
    Each request must be a dictionary. Unknown resources make the allocation
    infeasible, as do exceeded capacities or fully consumed resources.

    Returns:
        True if all requests fit and at least one resource has capacity left.
        False otherwise, including when no resources are available.

    Raises:
        TypeError: If input types are invalid (not dict/list, keys not strings,
            values not numbers).
        ValueError: If a capacity or requested amount is negative.
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
    unknown_resource = False

    # ---- Process all requests, including validation after infeasibility ----
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
                unknown_resource = True
            else:
                used[rname] += amount

    # ---- Check capacity constraints ----
    if unknown_resource:
        return False
    for rname, cap in resources.items():
        if used[rname] > cap:
            return False

    # ---- Ensure at least one resource has capacity remaining ----
    return any(used[rname] < cap for rname, cap in resources.items())
