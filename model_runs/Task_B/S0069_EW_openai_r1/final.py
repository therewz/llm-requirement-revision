from typing import Dict, List, Union
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether every request can use one of its resource/amount options."""
    if resources is None:
        raise TypeError("Resources cannot be None")
    if requests is None:
        raise TypeError("Requests cannot be None")
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    for key, val in resources.items():
        if not isinstance(key, str):
            raise TypeError("Resource keys must be strings")
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise TypeError("Resource values must be numbers")
        if val < 0 or (isinstance(val, float) and not math.isfinite(val)):
            raise ValueError("Resource values must be non-negative finite numbers")

    resource_indices = {key: index for index, key in enumerate(resources)}
    capacities = tuple(resources.values())
    choices = []
    for req in requests:
        if not isinstance(req, dict):
            raise TypeError("Each request must be a dictionary")
        options = []
        for key, val in req.items():
            if not isinstance(key, str):
                raise TypeError("Request keys must be strings")
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise TypeError("Request values must be numbers")
            # Invalid options cannot satisfy a request, but another option may.
            if key not in resource_indices or val < 0:
                continue
            if isinstance(val, float) and not math.isfinite(val):
                continue
            index = resource_indices[key]
            if val <= capacities[index]:
                options.append((index, val))
        if not options:
            return False
        # A valid zero-cost option satisfies this request without using capacity.
        if not any(amount == 0 for _, amount in options):
            choices.append(options)

    # Try the most constrained requests first; alternatives still need a joint
    # search, since a locally valid choice can block a later request.
    choices.sort(key=len)
    stack = [(0, capacities)]
    seen = set()
    while stack:
        position, remaining = stack.pop()
        if position == len(choices):
            return True  # Exhausting every resource is allowed.
        state = (position, remaining)
        if state in seen:
            continue
        seen.add(state)
        for index, amount in choices[position]:
            if amount <= remaining[index]:
                updated = list(remaining)
                updated[index] -= amount
                stack.append((position + 1, tuple(updated)))

    return False
