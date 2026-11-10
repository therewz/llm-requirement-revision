from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests fit within the available resources.

    Args:
        resources: Mapping of resource names to available capacity.
        requests: List of dictionaries mapping resource names to requested quantities.

    Returns:
        True if total demand for each resource is less than or equal to its
        available capacity, otherwise False. Missing resources have zero capacity.
    """
    total_demand: Dict[str, Number] = {res: 0 for res in resources}
    for request in requests:
        for res, qty in request.items():
            total_demand[res] = total_demand.get(res, 0) + qty

    return all(
        demand <= resources.get(res, 0)
        for res, demand in total_demand.items()
    )
