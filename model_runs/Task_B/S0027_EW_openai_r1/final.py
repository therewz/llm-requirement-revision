from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests fit within the available resource capacities.

    Args:
        resources: Mapping from resource name to total available capacity.
        requests: List of mappings from resource name to the amount required.

    Returns:
        True if every resource's total demand is within its capacity, including
        when all available resources are consumed. False for infeasible
        allocations, negative amounts, or malformed inputs.
    """
    if not isinstance(resources, dict) or not isinstance(requests, list):
        return False

    for resource_name, capacity in resources.items():
        if (
            not isinstance(resource_name, str)
            or not isinstance(capacity, (int, float))
            or not capacity >= 0
        ):
            return False

    total_demand: Dict[str, Number] = {}
    for request in requests:
        if not isinstance(request, dict):
            return False
        for resource_name, amount in request.items():
            if (
                not isinstance(resource_name, str)
                or not isinstance(amount, (int, float))
                or not amount >= 0
            ):
                return False
            total_demand[resource_name] = total_demand.get(resource_name, 0) + amount

    for resource_name, demand in total_demand.items():
        if resource_name not in resources or demand > resources[resource_name]:
            return False

    return True
