from typing import Dict, List, Union
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether all requests fit within the shared resource capacities.

    Empty request lists and exact capacity matches are allowed. Invalid inputs,
    unknown resources, and requests exceeding the available capacity return False.
    """
    if not isinstance(resources, dict) or not isinstance(requests, list):
        return False

    # Validate capacities before considering requests, including an empty list.
    for r_key, r_val in resources.items():
        if not isinstance(r_key, str):
            return False
        if not isinstance(r_val, (int, float)) or isinstance(r_val, bool):
            return False
        if r_val < 0 or (isinstance(r_val, float) and not math.isfinite(r_val)):
            return False

    total_used = {resource: 0 for resource in resources}

    for request in requests:
        if not isinstance(request, dict):
            return False
        for req_key, req_val in request.items():
            if not isinstance(req_key, str) or req_key not in resources:
                return False
            if not isinstance(req_val, (int, float)) or isinstance(req_val, bool):
                return False
            if req_val < 0 or (isinstance(req_val, float) and not math.isfinite(req_val)):
                return False

            total_used[req_key] += req_val
            if total_used[req_key] > resources[req_key]:
                return False

    return True
