from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Choose one resource/amount option per request, leaving capacity unused."""
    capacities = tuple(resources.values())
    if any(capacity < 0 for capacity in capacities):
        return False
    if not any(capacity > 0 for capacity in capacities):
        return False

    resource_indices = {resource: index for index, resource in enumerate(resources)}
    request_options = []
    for request in requests:
        options = []
        for resource, amount in request.items():
            if resource not in resource_indices:
                continue
            index = resource_indices[resource]
            if 0 <= amount <= capacities[index]:
                options.append((index, amount))
        if not options:
            return False
        # A valid zero-cost option always satisfies this request without
        # restricting any other request or consuming the required spare capacity.
        if any(amount == 0 for _, amount in options):
            continue
        request_options.append(options)

    # Try the most constrained requests first. Search all viable choices rather
    # than committing greedily to one resource for each request.
    request_options.sort(key=len)
    pending = [(0, capacities)]
    seen = set()
    while pending:
        position, remaining = pending.pop()
        state = (position, remaining)
        if state in seen:
            continue
        seen.add(state)

        if not any(capacity > 0 for capacity in remaining):
            continue
        if position == len(request_options):
            return True

        for index, amount in request_options[position]:
            if amount <= remaining[index]:
                updated = list(remaining)
                updated[index] -= amount
                pending.append((position + 1, tuple(updated)))

    return False
