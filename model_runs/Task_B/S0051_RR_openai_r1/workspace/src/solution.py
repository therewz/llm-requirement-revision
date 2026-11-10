
"""
Stub file for the is allocation feasible exercise.

Implement the function `is_allocation_feasible` to  Determine whether a set of resource requests can be satisfied 
given limited capacities. Take int account any possible constraints. See the task description
for full requirements.
"""
    
from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether requests fit while leaving some resource capacity unused.

    Args:
        resources : Dict[str, Number], Mapping from resource name to total available capacity.
        requests : List[Dict[str, Number]], List of requests. Each request is a mapping from resource name to the amount required.

    Returns:
        True if no resource is overallocated and at least one has unused capacity.

    """
    requested = {resource: [] for resource in resources}

    for request in requests:
        if not isinstance(request, dict):
            raise ValueError(f"Each request must be a dictionary, got {type(request).__name__}")

        for resource, amount in request.items():
            if resource not in requested:
                return False
            requested[resource].append(amount)

    has_unused_capacity = False
    for resource, capacity in resources.items():
        # Sum in a consistent order, including equal-valued ints and floats,
        # so floating-point rounding cannot depend on request order.
        amounts = sorted(
            requested[resource], key=lambda amount: (amount, type(amount).__name__)
        )
        total = sum(amounts)
        if total > capacity:
            return False
        if total < capacity:
            has_unused_capacity = True

    return has_unused_capacity
