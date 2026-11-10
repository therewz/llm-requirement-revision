from typing import Dict, List, Union

Number = Union[int, float]


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.
    Allocation is all or nothing: every request must be fully satisfiable.

    Args:
        resources: Dict[str, Number] - Mapping from resource name to total available capacity.
        requests: List[Dict[str, Number]] - Each request is a mapping from resource name to the amount required.
            A single request dict is also accepted.

    Returns:
        True if the total demand for every resource fits within capacity.
        False otherwise (including negative values or wrong input format).
    """
    # Validate resources
    if not isinstance(resources, dict):
        return False
    for name, capacity in resources.items():
        if not isinstance(name, str) or not _is_number(capacity) or capacity < 0:
            return False

    # Validate requests
    if isinstance(requests, dict):
        requests = [requests]
    if not isinstance(requests, (list, tuple)):
        return False
    for request in requests:
        if not isinstance(request, dict):
            return False

    # Sum total demand per resource
    total_demand: Dict[str, Number] = {}
    for request in requests:
        for resource_name, amount in request.items():
            if not isinstance(resource_name, str) or not _is_number(amount) or amount < 0:
                return False
            total_demand[resource_name] = total_demand.get(resource_name, 0) + amount

    # Check feasibility
    for resource_name, demand in total_demand.items():
        if resource_name not in resources:
            return False  # requested resource doesn't exist
        if demand > resources[resource_name]:
            return False  # demand exceeds capacity

    return True
