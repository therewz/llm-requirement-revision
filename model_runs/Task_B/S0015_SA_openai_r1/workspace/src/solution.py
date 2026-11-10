from typing import Dict, List, Union
from collections import defaultdict

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Return whether total demand for each resource fits its available capacity.

    Resources not listed in `resources` have zero capacity. Exact-capacity
    allocations and empty sets of requests are feasible; no spare capacity is
    required. Inputs are assumed to be in a reasonable, consistent format.
    """
    total_demand: Dict[str, Number] = defaultdict(int)

    for request in requests:
        for resource, amount in request.items():
            total_demand[resource] += amount

    return all(
        demand <= resources.get(resource, 0)
        for resource, demand in total_demand.items()
    )
