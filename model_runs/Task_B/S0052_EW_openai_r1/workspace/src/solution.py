
"""
Stub file for the is allocation feasible exercise.

Implement the function `is_allocation_feasible` to  Determine whether a set of resource requests can be satisfied 
given limited capacities. Take int account any possible constraints. See the task description
for full requirements.
"""
    
from math import isfinite
from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Args:
        resources : Dict[str, Number], Mapping from resource name to total available capacity.
        requests : List[Dict[str, Number]], List of requests. Each request is a mapping from resource name to the amount required.

    Returns:
        True if the allocation is feasible, False otherwise.

    """
    #raise NotImplementedError("suggest_slots function has not been implemented yet")

    """
    Determine whether a set of resource requests can be satisfied
    given limited capacities.
    """

    # Validate resources structure and capacities.
    if not isinstance(resources, dict):
        raise ValueError("Resources must be a dictionary.")

    for capacity in resources.values():
        if not isinstance(capacity, (int, float)):
            raise ValueError("Resource amounts must be numeric.")
        if capacity < 0 or (isinstance(capacity, float) and not isfinite(capacity)):
            return False

    # Initialize usage tracker
    total_usage: Dict[str, Number] = {r: 0 for r in resources}

    for request in requests:
        # Structural validation
        if not isinstance(request, dict):
            raise ValueError("Each request must be a dictionary.")

        for resource_name, amount in request.items():
            # Resource must exist
            if resource_name not in resources:
                return False

            # Amount must be numeric
            if not isinstance(amount, (int, float)):
                raise ValueError("Resource amounts must be numeric.")

            # Requests must be finite and non-negative.
            if amount < 0 or (isinstance(amount, float) and not isfinite(amount)):
                return False

            total_usage[resource_name] += amount

    # Check capacity constraints
    for resource_name, used in total_usage.items():
        if used > resources[resource_name]:
            return False

    return True