from typing import Dict, List, Union
from fractions import Fraction
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
    """Return whether all requests fit within the available capacities.

    Requests may be dictionaries or (resource_id, amount) tuples. Empty inputs
    and allocations that use all available capacity are allowed.

    Raises:
        TypeError: If the input containers or request entries are malformed.
        ValueError: If a capacity or amount is not a finite, non-negative number.

    A request for an unavailable resource makes the allocation infeasible.
    """
    if not isinstance(resources, dict):
        raise TypeError("resources must be a dict mapping resource name to capacity")
    if not isinstance(requests, list):
        raise TypeError("requests must be a list of request dicts or tuples")

    capacities = {}
    for name, cap in resources.items():
        if not _is_finite_number(cap):
            raise ValueError(f"capacity for resource '{name}' must be a finite number")
        if cap < 0:
            raise ValueError(f"capacity for resource '{name}' must be non-negative")
        capacities[name] = Fraction(cap)

    # Exact sums prevent rounding from hiding an excess, including when large
    # integer capacities are combined with floating-point request amounts.
    totals = {name: Fraction(0) for name in capacities}
    all_resources_present = True
    for req in requests:
        if isinstance(req, dict):
            items = req.items()
        elif isinstance(req, tuple) and len(req) == 2:
            items = (req,)
        else:
            raise TypeError("each request must be a dict or a (resource_id, amount) tuple")

        for name, amount in items:
            if not _is_finite_number(amount):
                raise ValueError(f"request amount for resource '{name}' must be a finite number")
            if amount < 0:
                raise ValueError(f"request amount for resource '{name}' must be non-negative")
            if name not in capacities:
                all_resources_present = False
            else:
                totals[name] += Fraction(amount)

    return all_resources_present and all(
        totals[name] <= capacity for name, capacity in capacities.items()
    )
