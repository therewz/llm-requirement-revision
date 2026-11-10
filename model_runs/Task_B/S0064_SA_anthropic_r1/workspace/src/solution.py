from typing import Dict, List
import numbers
import math


def _is_valid_amount(value) -> bool:
    """True if value is a real, non-negative, non-NaN number (bool excluded)."""
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
    Determines if a set of resource requests can be satisfied given available capacities.

    Args:
        resources: Mapping of resource names to available (non-negative numeric) capacity.
        requests: List of requests, each a dict mapping resource names to required amounts.

    Returns:
        True if, for every resource, the total requested amount across all requests
        does not exceed its capacity. False if any capacity or request amount is
        negative/non-numeric, if a request references an undefined resource, or if
        any capacity would be exceeded.

    Raises:
        ValueError: If any request is not a dictionary.
    """
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list of dictionaries.")

    # Every request must be a dictionary.
    for req in requests:
        if not isinstance(req, dict):
            raise ValueError("Each request must be a dictionary.")

    # Capacities must be numeric and non-negative.
    for capacity in resources.values():
        if not _is_valid_amount(capacity):
            return False

    # Aggregate requested amounts across all requests.
    totals = {name: 0 for name in resources}
    for req in requests:
        for name, amount in req.items():
            if name not in resources:
                return False
            if not _is_valid_amount(amount):
                return False
            totals[name] += amount

    # Total allocation must not exceed capacity for any resource.
    return all(totals[name] <= resources[name] for name in resources)
