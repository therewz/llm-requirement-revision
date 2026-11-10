from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Check simultaneous demand, requiring some capacity to remain unused.

    Resource names are matched case-sensitively. Unknown resources, unknown
    capacities, and negative values make the allocation infeasible. Neither
    input is modified.
    """
    for capacity in resources.values():
        if capacity is None or not capacity >= 0:
            return False

    aggregated_demand = {resource: 0 for resource in resources}
    for request in requests:
        for resource, amount in request.items():
            if resource not in resources:
                return False
            if amount is None or not amount >= 0:
                return False
            aggregated_demand[resource] += amount

    has_unused_capacity = False
    for resource, capacity in resources.items():
        demand = aggregated_demand[resource]
        if not demand <= capacity:
            return False
        if demand < capacity:
            has_unused_capacity = True

    return has_unused_capacity
