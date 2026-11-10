from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether all requests fit within the available capacities.

    Demands for each case-sensitive resource name are added across all
    requests. Unknown resources and negative capacities or demands are
    infeasible. Empty requests and exact-capacity allocations are valid.
    Neither input is modified.
    """
    if any(capacity < 0 for capacity in resources.values()):
        return False

    aggregated_demand: Dict[str, Number] = {}
    for request in requests:
        for resource, amount in request.items():
            if resource not in resources or amount < 0:
                return False
            aggregated_demand[resource] = (
                aggregated_demand.get(resource, 0) + amount
            )

    return all(
        total <= resources[resource]
        for resource, total in aggregated_demand.items()
    )
