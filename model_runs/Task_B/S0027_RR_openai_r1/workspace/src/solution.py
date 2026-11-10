from typing import Dict, List, Union

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Return whether all requests fit and some available capacity remains.

    Resources and requests map string resource names to non-negative integers.
    Requests may be a list of mappings or a single request mapping. Invalid
    inputs return False.
    """
    if not isinstance(resources, dict):
        return False
    for resource_name, capacity in resources.items():
        if (not isinstance(resource_name, str)
                or not isinstance(capacity, int)
                or isinstance(capacity, bool)
                or capacity < 0):
            return False

    if isinstance(requests, dict):
        requests = [requests]
    elif not isinstance(requests, list):
        return False

    total_demand: Dict[str, Number] = {}
    for request in requests:
        if not isinstance(request, dict):
            return False
        for resource_name, amount in request.items():
            if (not isinstance(resource_name, str)
                    or not isinstance(amount, int)
                    or isinstance(amount, bool)
                    or amount < 0):
                return False
            if resource_name not in resources:
                return False
            total_demand[resource_name] = total_demand.get(resource_name, 0) + amount

    if any(demand > resources[name] for name, demand in total_demand.items()):
        return False

    return any(capacity > total_demand.get(name, 0)
               for name, capacity in resources.items())
