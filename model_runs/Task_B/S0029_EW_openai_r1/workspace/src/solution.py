from typing import Dict, List, Union
import math

Number = Union[int, float]

def _is_finite_number(x: object) -> bool:
    return (
        isinstance(x, (int, float))
        and not isinstance(x, bool)
        and (isinstance(x, int) or math.isfinite(x))
    )

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests can be satisfied without exceeding capacities.

    Fully consuming the available resources is allowed. Requests for unknown
    resources make the allocation infeasible.

    Raises:
        TypeError: If inputs or resource/request keys are of incorrect type.
        ValueError: If capacities or request amounts are not finite, non-negative numbers.
    """
    # ------------------------
    # TYPE CHECKS
    # ------------------------
    if not isinstance(resources, dict):
        raise TypeError("resources must be a dict mapping resource name to capacity")
    if not isinstance(requests, list):
        raise TypeError("requests must be a list of request dicts")

    # ------------------------
    # VALIDATE RESOURCES
    # ------------------------
    capacities: Dict[str, Number] = {}
    for name, cap in resources.items():
        if not isinstance(name, str):
            raise TypeError("resource names must be strings")
        if not _is_finite_number(cap):
            raise ValueError(f"capacity for resource '{name}' must be a finite number")
        if cap < 0:
            raise ValueError(f"capacity for resource '{name}' must be non-negative")
        capacities[name] = cap

    totals: Dict[str, Number] = {name: 0 for name in capacities}
    feasible = True

    # ------------------------
    # VALIDATE REQUESTS
    # ------------------------
    for req in requests:
        if not isinstance(req, dict):
            raise TypeError("each request must be a dict mapping resource name to amount required")
        for name, amount in req.items():
            if not isinstance(name, str):
                raise TypeError("request keys must be strings")
            if not _is_finite_number(amount):
                raise ValueError(f"request amount for resource '{name}' must be a finite number")
            if amount < 0:
                raise ValueError(f"request amount for resource '{name}' must be non-negative")
            if name not in capacities:
                feasible = False
                continue
            totals[name] += amount
            if totals[name] > capacities[name]:
                feasible = False

    return feasible
