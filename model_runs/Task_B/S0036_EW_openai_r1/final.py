from typing import Dict, List, Union
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether the requests fit within the shared resource capacities.

    Invalid inputs return False. Empty requests and allocations that exactly
    consume the available resources are valid.
    """
    if not isinstance(resources, dict) or not isinstance(requests, list):
        return False

    def valid_number(value: Number) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value >= 0
            and (not isinstance(value, float) or math.isfinite(value))
        )

    for resource, capacity in resources.items():
        if not isinstance(resource, str) or not valid_number(capacity):
            return False

    total_used = {resource: 0 for resource in resources}
    for request in requests:
        if not isinstance(request, dict):
            return False
        for resource, amount in request.items():
            if not isinstance(resource, str) or not valid_number(amount):
                return False
            if resource not in resources:
                return False

            total_used[resource] += amount
            if total_used[resource] > resources[resource]:
                return False

    return True
