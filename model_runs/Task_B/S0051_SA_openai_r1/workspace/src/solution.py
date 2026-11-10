"""Check whether resource requests fit within available capacities."""

from fractions import Fraction
from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests can be satisfied given limited capacities.

    Missing resources in a request require zero units. Unknown resource names
    make the allocation infeasible, even when the requested amount is zero.
    Exact capacity usage and empty request lists are feasible.

    The inputs are assumed to contain nonnegative numeric capacities and amounts.
    Neither input is modified.
    """
    totals = {resource: Fraction(0) for resource in resources}

    for request in requests:
        for resource, amount in request.items():
            if resource not in resources or amount > resources[resource]:
                return False
            # Sum exact numeric values so request order cannot change the result
            # through intermediate floating-point rounding.
            totals[resource] += Fraction(amount)
            if totals[resource] > resources[resource]:
                return False

    return True
