from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Return whether all requests fit within the independent resource capacities.

    Resource names must be strings, and capacities and requested amounts must
    be non-negative integers. Invalid inputs return False. Exact capacity usage
    is allowed, and neither input is modified.
    """
    if not isinstance(resources, dict) or not isinstance(requests, list):
        return False

    for resource_name, capacity in resources.items():
        if (
            not isinstance(resource_name, str)
            or not isinstance(capacity, int)
            or isinstance(capacity, bool)
            or capacity < 0
        ):
            return False

    total_demand: Dict[str, Number] = {}
    for request in requests:
        if not isinstance(request, dict):
            return False
        for resource_name, amount in request.items():
            if (
                not isinstance(resource_name, str)
                or not isinstance(amount, int)
                or isinstance(amount, bool)
                or amount < 0
            ):
                return False
            total_demand[resource_name] = total_demand.get(resource_name, 0) + amount

    return all(
        resource_name in resources and demand <= resources[resource_name]
        for resource_name, demand in total_demand.items()
    )
