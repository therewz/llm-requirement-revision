from typing import Dict, List, Union
from fractions import Fraction
import math

Number = Union[int, float]


def _is_finite_number(x: object) -> bool:
    return (
        isinstance(x, int) and not isinstance(x, bool)
        or isinstance(x, float) and math.isfinite(x)
    )


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Check that every request fits and some available capacity remains unused.

    Requests may be dictionaries or (resource_id, amount) tuples. Unknown
    resources make the allocation infeasible, including zero-amount requests.

    Raises:
        TypeError: If the input containers or request entries have invalid types.
        ValueError: If a capacity or request amount is not a finite, non-negative
            integer or float.
    """
    if not isinstance(resources, dict):
        raise TypeError("resources must be a dict mapping resource IDs to capacity")
    if not isinstance(requests, list):
        raise TypeError("requests must be a list of request dicts or tuples")

    # Use exact arithmetic for the supplied numeric values, avoiding precision
    # loss that could otherwise hide an over-capacity request.
    capacities = {}
    for name, cap in resources.items():
        if not _is_finite_number(cap):
            raise ValueError(f"capacity for resource '{name}' must be a finite number")
        if cap < 0:
            raise ValueError(f"capacity for resource '{name}' must be non-negative")
        capacities[name] = Fraction(cap)

    totals = {name: Fraction(0) for name in capacities}
    unknown_resource = False
    for req in requests:
        if isinstance(req, dict):
            entries = req.items()
        elif isinstance(req, tuple) and len(req) == 2:
            entries = (req,)
        else:
            raise TypeError("each request must be a dict or a (resource_id, amount) tuple")

        for name, amount in entries:
            if not _is_finite_number(amount):
                raise ValueError(f"request amount for resource '{name}' must be a finite number")
            if amount < 0:
                raise ValueError(f"request amount for resource '{name}' must be non-negative")
            if name not in capacities:
                unknown_resource = True
            else:
                totals[name] += Fraction(amount)

    if unknown_resource:
        return False
    if any(totals[name] > cap for name, cap in capacities.items()):
        return False

    # An empty or fully consumed resource pool has no unused capacity.
    return any(totals[name] < cap for name, cap in capacities.items())
