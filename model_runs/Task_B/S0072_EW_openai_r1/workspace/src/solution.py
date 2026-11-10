from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests fit within the available resource capacities.

    Inputs are assumed to contain reasonable, consistent numeric values.
    Missing resource capacities are treated as zero. Exact-capacity allocations
    are feasible, and neither input is modified.
    """
    total_requested = {res: 0 for res in resources}
    for request in requests:
        for resource, amount in request.items():
            total_requested[resource] = total_requested.get(resource, 0) + amount

    return all(
        total <= resources.get(resource, 0)
        for resource, total in total_requested.items()
    )
