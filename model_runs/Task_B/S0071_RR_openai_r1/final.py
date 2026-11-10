from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Check all requests together, requiring some capacity to remain unused."""
    # Validate every request before checking feasibility, so a malformed request
    # is reported even when another request cannot be satisfied.
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("Each request must be a dictionary.")

    total_requested = {resource: 0 for resource in resources}
    for request in requests:
        for resource, amount in request.items():
            if resource not in resources:
                return False
            total_requested[resource] += amount

    has_unused_capacity = False
    for resource, capacity in resources.items():
        total = total_requested[resource]
        if not total <= capacity:
            return False
        if total < capacity:
            has_unused_capacity = True

    # Empty or fully consumed resources leave no capacity unallocated.
    return has_unused_capacity
