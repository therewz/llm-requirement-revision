from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether the combined requests fit each defined resource capacity.

    Every request must be a dictionary; otherwise, raise ValueError.
    Requests for undefined resources are infeasible, even for zero amounts.
    """
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be provided as a list of dictionaries.")

    # Validate every request before evaluating feasibility.
    for req in requests:
        if not isinstance(req, dict):
            raise ValueError("Each request must be a dictionary.")

    total_requested = {resource: 0 for resource in resources}
    for req in requests:
        for resource, amount in req.items():
            if resource not in resources:
                return False
            total_requested[resource] += amount

    return all(
        total <= resources[resource]
        for resource, total in total_requested.items()
    )
