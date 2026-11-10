from typing import Dict, List
import numbers
import math


def _valid_number(value) -> bool:
    """True if value is a real, non-bool, non-NaN, non-negative number."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        return False
    if math.isnan(value):
        return False
    return value >= 0


def is_allocation_feasible(
    resources: Dict[str, numbers.Number],
    requests: List[Dict[str, numbers.Number]]
) -> bool:
    """
    Determines if a set of resource requests can be allocated given available
    capacities, while at least one resource remains partially unallocated.

    Returns True only if:
      - all capacities and request amounts are numeric and non-negative,
      - every requested resource exists in resources,
      - the total requested per resource does not exceed its capacity,
      - at least one resource has capacity left over after all requests.
    Returns False for invalid (negative / non-numeric / unknown-resource)
    values or when the allocation is infeasible.

    Raises:
        ValueError: If any request is not a dictionary.
        TypeError: If resources is not a dict or requests is not a list.
    """
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list of dictionaries.")

    # Every request must be a dictionary (checked before anything else).
    for req in requests:
        if not isinstance(req, dict):
            raise ValueError("Each request must be a dictionary.")

    # Validate capacities
    for capacity in resources.values():
        if not _valid_number(capacity):
            return False

    # Aggregate requests across all requests
    total_allocated = {name: 0 for name in resources}
    for req in requests:
        for name, amount in req.items():
            if name not in resources:
                return False
            if not _valid_number(amount):
                return False
            total_allocated[name] += amount

    # Capacity must not be exceeded
    for name, total in total_allocated.items():
        if total > resources[name]:
            return False

    # At least one resource must remain unallocated
    return any(total_allocated[name] < resources[name] for name in resources)
