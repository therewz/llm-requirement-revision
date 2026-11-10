from typing import Dict, List, Union

Number = Union[int, float]


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: Union[Dict[str, Number], List[Dict[str, Number]]]
) -> bool:
    """
    Determine whether resource requests can be satisfied given limited capacities,
    with at least one resource left partly unallocated afterwards.

    Args:
        resources: Mapping from resource name to available capacity (non-negative).
        requests: Either a single mapping of resource name to amount required, or a
            list of such mappings (demands are summed per resource).

    Returns:
        True if all demands fit (all or nothing) and at least one resource still has
        remaining capacity > 0 after allocation. False otherwise, including for
        malformed input or negative values.
    """
    # Validate resources
    if not isinstance(resources, dict):
        return False
    for name, cap in resources.items():
        if not isinstance(name, str) or not _is_number(cap) or cap < 0:
            return False

    # Normalize requests
    if isinstance(requests, dict):
        request_list = [requests]
    elif isinstance(requests, (list, tuple)):
        request_list = list(requests)
    else:
        return False

    total_demand: Dict[str, Number] = {}
    for request in request_list:
        if not isinstance(request, dict):
            return False
        for name, amount in request.items():
            if not isinstance(name, str) or not _is_number(amount) or amount < 0:
                return False
            total_demand[name] = total_demand.get(name, 0) + amount

    # Check capacity
    remaining = dict(resources)
    for name, demand in total_demand.items():
        if name not in resources:
            return False
        if demand > resources[name]:
            return False
        remaining[name] -= demand

    # At least one resource must remain unallocated
    return any(amount > 0 for amount in remaining.values())
