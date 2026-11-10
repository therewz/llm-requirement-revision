from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests fit within the available resource capacities.

    Requests for the same resource are summed across the list. An allocation is
    feasible only if no capacity is exceeded and some capacity remains unused.
    A resource not present in resources has zero available capacity.
    """
    total_demand: Dict[str, Number] = {}
    for request in requests:
        for resource, quantity in request.items():
            total_demand[resource] = total_demand.get(resource, 0) + quantity

    if any(
        demand > resources.get(resource, 0)
        for resource, demand in total_demand.items()
    ):
        return False

    return any(
        total_demand.get(resource, 0) < available
        for resource, available in resources.items()
    )
