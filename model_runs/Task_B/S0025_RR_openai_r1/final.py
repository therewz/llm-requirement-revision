from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether all requests fit and some resource capacity remains unused."""
    total_demand: Dict[str, Number] = {resource: 0 for resource in resources}
    for request in requests:
        for resource, amount in request.items():
            total_demand[resource] = total_demand.get(resource, 0) + amount

    # A resource that is not available has zero capacity.
    for resource, demand in total_demand.items():
        if demand > resources.get(resource, 0):
            return False

    return any(
        total_demand[resource] < capacity
        for resource, capacity in resources.items()
    )
