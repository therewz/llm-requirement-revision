from fractions import Fraction
from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests fit within the available resource capacities.

    Each request maps resource names to non-negative int or float amounts.
    Return False for invalid inputs, unknown resources, or exceeded capacities.
    Resources may be fully consumed, and an empty set of requests is feasible.
    """
    if not isinstance(resources, dict) or not isinstance(requests, list):
        return False

    for key, value in resources.items():
        if not isinstance(key, str):
            return False
        if not isinstance(value, (int, float)) or not value >= 0:
            return False

    # Exact totals avoid floating-point accumulation depending on request order.
    used = {resource: Fraction(0) for resource in resources}
    infinity = float("inf")

    for request in requests:
        if not isinstance(request, dict):
            return False

        for key, value in request.items():
            if not isinstance(key, str) or key not in resources:
                return False
            if not isinstance(value, (int, float)) or not value >= 0:
                return False

            # A non-negative numeric amount always fits an unlimited capacity.
            if resources[key] == infinity:
                continue
            if value == infinity:
                return False

            used[key] += Fraction(value)
            if used[key] > resources[key]:
                return False

    return True
