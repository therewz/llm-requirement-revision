from typing import Dict, List, Union

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities,
    with the additional requirement that some resource capacity remains unallocated.

    Args:
        resources: Dict[str, Number] - mapping from resource name to total available capacity.
        requests: List[Dict[str, Number]] - list of requests. Each request is a mapping
                  from resource name to the amount required.

    Returns:
        True if the allocation is feasible and leaves positive unused capacity, False otherwise.
    """

    # Keep track of total demand per resource
    total_demand = {}

    for request in requests:
        for resource_name, amount in request.items():
            if resource_name not in resources:
                # Requesting a resource that does not exist
                return False
            total_demand[resource_name] = total_demand.get(resource_name, 0) + amount

    # Check if demand exceeds capacity
    for resource_name, demand_amount in total_demand.items():
        if demand_amount > resources[resource_name]:
            return False

    # Check if at least one resource has leftover capacity
    for resource_name, capacity in resources.items():
        used = total_demand.get(resource_name, 0)
        if used < capacity:
            return True  # Some capacity remains unallocated

    # If all resources are fully consumed, allocation is invalid
    return False
