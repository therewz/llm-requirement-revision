
"""
Stub file for the is allocation feasible exercise.

Implement the function `is_allocation_feasible` to  Determine whether a set of resource requests can be satisfied 
given limited capacities. Take int account any possible constraints. See the task description
for full requirements.
"""
    
from numbers import Real
from typing import Dict, List, Union

Number = Union[int, float]


def _valid_number(value) -> bool:
    """True for a non-bool real number that is >= 0 (NaN is rejected)."""
    return isinstance(value, Real) and not isinstance(value, bool) and value >= 0


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
    # Total requested amount per resource (missing resources count as 0)
    totals: Dict[str, Number] = {}

    for request in requests:
        if not isinstance(request, dict):
            raise ValueError(f"Each request must be a dictionary, got {type(request).__name__}")

        for resource, amount in request.items():
            if resource not in resources:
                return False
            if not _valid_number(amount):
                return False
            totals[resource] = totals.get(resource, 0) + amount

    for resource, total in totals.items():
        capacity = resources[resource]
        if not _valid_number(capacity):
            return False
        if total > capacity:
            return False

    return True
