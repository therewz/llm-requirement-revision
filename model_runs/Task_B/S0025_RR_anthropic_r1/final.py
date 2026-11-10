from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Return True if all requests can be satisfied within the available capacities
    AND at least one resource retains unallocated capacity afterwards.
    """
    total_demand: Dict[str, Number] = {}
    for req in requests:
        for name, amount in req.items():
            total_demand[name] = total_demand.get(name, 0) + amount

    # Demand must not exceed capacity (a resource not listed has capacity 0).
    for name, demand in total_demand.items():
        if demand > resources.get(name, 0):
            return False

    # At least one resource must remain (partly) unallocated.
    return any(total_demand.get(name, 0) < capacity for name, capacity in resources.items())
