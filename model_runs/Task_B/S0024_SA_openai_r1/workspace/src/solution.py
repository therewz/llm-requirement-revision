"""Check whether resource requests fit within the available capacities."""

from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests can be satisfied by the available resources.

    Args:
        resources: Mapping from resource name to total available capacity.
        requests: List of mappings from resource name to the amount required.

    Returns:
        True if the allocation is feasible, False otherwise.
    """
    resources_copy = {k: v for k, v in resources.items()}
    for request in requests:
        for resource, amount in request.items():
            if resource not in resources:
                return False
            if amount > resources_copy[resource]:
                return False
            resources_copy[resource] -= amount
    return True
