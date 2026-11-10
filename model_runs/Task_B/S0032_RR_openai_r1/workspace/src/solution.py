from typing import Dict, List, Union
from fractions import Fraction
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Return whether all requests fit and at least one resource has unused capacity.

    Resources and requests must map string resource names to non-negative int or
    float amounts. Invalid inputs, including requests for unknown resources,
    return False. Empty or fully consumed capacity is not feasible.
    """
    if not isinstance(resources, dict) or not isinstance(requests, list):
        return False

    for key, value in resources.items():
        if not isinstance(key, str):
            return False
        if not isinstance(value, (int, float)) or not value >= 0:
            return False

    used = {resource: 0 for resource in resources}

    for request in requests:
        if not isinstance(request, dict):
            return False

        for key, value in request.items():
            if not isinstance(key, str) or key not in resources:
                return False
            if not isinstance(value, (int, float)) or not value >= 0:
                return False

            # Sum finite amounts exactly so request order cannot change the result.
            # Non-negative infinity is permitted by the numeric input contract.
            if value == math.inf:
                used[key] = math.inf
            elif used[key] != math.inf:
                used[key] += Fraction(value)

            if used[key] > resources[key]:
                return False

    return any(used[key] < capacity for key, capacity in resources.items())
