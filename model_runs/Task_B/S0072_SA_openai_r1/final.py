from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether all requests fit within the available resource capacities.

    Inputs are assumed to be reasonable and consistent and are not modified.
    Resources not listed in a request require no allocation; resources not
    available have zero capacity. Exact-capacity allocations are feasible.
    """
    total_requested = {resource: 0 for resource in resources}
    for request in requests:
        for resource, amount in request.items():
            total_requested[resource] = total_requested.get(resource, 0) + amount

    return all(
        total <= resources.get(resource, 0)
        for resource, total in total_requested.items()
    )
