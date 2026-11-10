"""
Determine whether simultaneous resource requests fit within available capacities.

Demand for each resource is summed across all requests. Resources not present in
`resources` have capacity zero. A feasible allocation must leave some capacity
unallocated.
"""
from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Return whether all requests fit and at least one resource has capacity left.

    Inputs are assumed to be in a reasonable, consistent format, with
    non-negative capacities and request amounts.
    """
    total_demand: Dict[str, Number] = {}

    for req in requests:
        for rname, amount in req.items():
            total_demand[rname] = total_demand.get(rname, 0) + amount

    for rname, demand in total_demand.items():
        if demand > resources.get(rname, 0):
            return False

    return any(
        capacity > total_demand.get(rname, 0)
        for rname, capacity in resources.items()
    )
