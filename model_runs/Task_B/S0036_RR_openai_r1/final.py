from typing import Dict, List, Union
import math

Number = Union[int, float]


def _is_valid_amount(value: Number) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value >= 0
        and (not isinstance(value, float) or math.isfinite(value))
    )


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether requests fit and leave some resource capacity unused.

    Resource capacities and requested amounts must be non-negative finite
    numbers. Invalid inputs return False. Requests share the available
    capacities, and at least one resource must have a positive remainder.
    """
    if not isinstance(resources, dict) or not isinstance(requests, list):
        return False

    for resource, capacity in resources.items():
        if not isinstance(resource, str) or not _is_valid_amount(capacity):
            return False

    total_used = {resource: 0 for resource in resources}

    for request in requests:
        if not isinstance(request, dict):
            return False
        for resource, amount in request.items():
            if (
                not isinstance(resource, str)
                or resource not in resources
                or not _is_valid_amount(amount)
            ):
                return False

            total_used[resource] += amount
            if total_used[resource] > resources[resource]:
                return False

    return any(
        total_used[resource] < capacity
        for resource, capacity in resources.items()
    )
