from typing import Dict, List, Union
import math

Number = Union[int, float]

def _is_finite_number(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Returns True if, for every resource, the total requested amount does not exceed its
    capacity (exactly meeting capacity is allowed). Returns False if any request references
    a resource that is not available or if any capacity would be exceeded.

    Each request is a dict mapping resource name to amount (a (resource, amount) tuple
    is also accepted).

    Raises:
        TypeError: If inputs or resource/request keys/values are of incorrect type.
        ValueError: If capacities or amounts are negative, NaN, or infinite.
    """
    if not isinstance(resources, dict):
        raise TypeError("resources must be a dict mapping resource name to capacity")
    if not isinstance(requests, list):
        raise TypeError("requests must be a list of request dicts")

    capacities: Dict[str, float] = {}
    for name, cap in resources.items():
        if not isinstance(name, str):
            raise TypeError("resource names must be strings")
        if not _is_finite_number(cap):
            raise ValueError(f"capacity for resource '{name}' must be a finite number")
        cap_f = float(cap)
        if cap_f < 0:
            raise ValueError(f"capacity for resource '{name}' must be non-negative")
        capacities[name] = cap_f

    totals: Dict[str, float] = {}
    feasible = True

    for req in requests:
        if isinstance(req, dict):
            items = list(req.items())
        elif isinstance(req, tuple) and len(req) == 2:
            items = [req]
        else:
            raise TypeError("each request must be a dict mapping resource name to amount required")
        for name, amount in items:
            if not isinstance(name, str):
                raise TypeError("request keys must be strings")
            if not _is_finite_number(amount):
                raise ValueError(f"request amount for resource '{name}' must be a finite number")
            amt_f = float(amount)
            if amt_f < 0:
                raise ValueError(f"request amount for resource '{name}' must be non-negative")
            if name not in capacities:
                feasible = False
                continue
            totals[name] = totals.get(name, 0.0) + amt_f
            if totals[name] > capacities[name]:
                feasible = False

    return feasible
