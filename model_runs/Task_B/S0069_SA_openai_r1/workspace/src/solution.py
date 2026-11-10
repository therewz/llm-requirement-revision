from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether one resource/amount option per request can be allocated.

    Each request maps alternative resource types to the amount required if that
    option is selected. Invalid options (unknown resources or negative amounts)
    cannot be selected. Inputs are not modified.
    """
    if any(not capacity >= 0 for capacity in resources.values()):
        return False

    options = []
    for request in requests:
        valid_options = [
            (resource, amount)
            for resource, amount in request.items()
            if resource in resources and 0 <= amount <= resources[resource]
        ]
        if not valid_options:
            return False
        options.append(valid_options)

    if not options:
        return True

    # Try the most constrained requests first, but backtrack when necessary.
    options.sort(key=len)
    allocated = dict.fromkeys(resources, 0)
    stack = [iter(options[0])]
    chosen = []

    # Explicit search frames avoid a recursion-depth limit on request count.
    while stack:
        for resource, amount in stack[-1]:
            previous = allocated[resource]
            total = previous + amount
            if total <= resources[resource]:
                allocated[resource] = total
                chosen.append((resource, previous))
                if len(chosen) == len(options):
                    return True
                stack.append(iter(options[len(chosen)]))
                break
        else:
            stack.pop()
            if chosen:
                resource, previous = chosen.pop()
                allocated[resource] = previous

    return False
