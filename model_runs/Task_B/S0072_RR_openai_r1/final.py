from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests fit while leaving some capacity unallocated.

    Args:
        resources: Available capacity for each resource.
        requests: Required amounts for each request; omitted resources require zero.

    Returns:
        True if every request can be fully satisfied and at least one resource
        has positive remaining capacity, otherwise False. Inputs are not modified.
    """
    total_requested = {resource: 0 for resource in resources}
    for request in requests:
        for resource, amount in request.items():
            total_requested[resource] = total_requested.get(resource, 0) + amount

    # A resource not supplied has no available capacity.
    for resource, amount in total_requested.items():
        if amount > resources.get(resource, 0):
            return False

    return any(
        total_requested[resource] < capacity
        for resource, capacity in resources.items()
    )
