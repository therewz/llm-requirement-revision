from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether total demand for every resource fits its capacity.

    Requests are cumulative, and using a resource's full capacity is allowed.
    Resources not listed in ``resources`` have no available capacity.
    """
    total_demand: Dict[str, Number] = {resource: 0 for resource in resources}
    for request in requests:
        for resource, amount in request.items():
            total_demand[resource] = total_demand.get(resource, 0) + amount

    return all(
        demand <= resources.get(resource, 0)
        for resource, demand in total_demand.items()
    )
