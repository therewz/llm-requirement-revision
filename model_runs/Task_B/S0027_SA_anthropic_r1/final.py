import math
from typing import Dict, List, Union

Number = Union[int, float]


def _is_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and not (isinstance(value, float) and math.isnan(value))
    )


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: Union[Dict[str, Number], List[Dict[str, Number]]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited
    capacities. Allocation is all or nothing: the total demand for every
    resource must fit within its capacity.

    Args:
        resources: Mapping from resource name (str) to available capacity (non-negative number).
        requests: A mapping from resource name to amount required, or a list of
            such mappings (their demands are summed per resource).

    Returns:
        True if every request can be fully satisfied, False otherwise
        (including malformed input or negative amounts).
    """
    # Validate resources
    if not isinstance(resources, dict):
        return False
    for name, capacity in resources.items():
        if not isinstance(name, str) or not _is_number(capacity) or capacity < 0:
            return False

    # Normalize requests
    if isinstance(requests, dict):
        request_list = [requests]
    elif isinstance(requests, (list, tuple)):
        request_list = list(requests)
    else:
        return False

    # Sum total demand per resource
    total_demand: Dict[str, Number] = {}
    for request in request_list:
        if not isinstance(request, dict):
            return False
        for name, amount in request.items():
            if not isinstance(name, str) or not _is_number(amount) or amount < 0:
                return False
            total_demand[name] = total_demand.get(name, 0) + amount

    # Check capacity
    for name, demand in total_demand.items():
        if name not in resources:
            return False
        if demand > resources[name]:
            return False

    return True
