from typing import Dict, List, Union

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Args:
        resources: Dict[str, Number] - mapping from resource name to total available capacity.
        requests: List[Dict[str, Number]] - list of requests. Each request is a mapping
                  from resource name to the amount required.

    Returns:
        True if the total demand for every resource fits within its capacity, False otherwise.
    """
    
    # Keep track of total demand per resource
    total_demand = {}

    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("All requests must be dictionaries.")
        
        for resource_name, amount in request.items():
            if resource_name not in resources:
                # Requesting a resource that does not exist
                return False
            total_demand[resource_name] = total_demand.get(resource_name, 0) + amount

    # Check if demand exceeds capacity
    for resource_name, demand_amount in total_demand.items():
        if demand_amount > resources[resource_name]:
            return False

    return True
