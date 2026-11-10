from typing import Dict, List, Union
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determines whether all requests can be satisfied simultaneously
    given the available resources, ensuring at least one resource
    remains unallocated (some resource's aggregated demand is strictly
    below its capacity).

    Returns False if a request references an unknown resource or if any
    aggregated demand exceeds capacity. Inputs are never modified.

    Raises:
        TypeError: For invalid types (non-numeric, booleans, strings)
        ValueError: For negative numbers, NaNs or infinities
    """

    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    for r, cap in resources.items():
        if not isinstance(r, str):
            raise TypeError(f"Resource key must be string, got {type(r).__name__}")
        if isinstance(cap, bool) or not isinstance(cap, (int, float)):
            raise TypeError(f"Resource '{r}' must be a number, got {type(cap).__name__}")
        if cap < 0 or math.isnan(cap) or math.isinf(cap):
            raise ValueError(f"Resource '{r}' has invalid capacity: {cap}")

    aggregated_demand: Dict[str, Number] = {r: 0 for r in resources}
    unknown_resource = False

    # Validate everything first (atomic processing), then decide.
    for idx, req in enumerate(requests):
        if not isinstance(req, dict):
            raise TypeError(f"Request at index {idx} is not a dictionary")

        for res, amt in req.items():
            if not isinstance(res, str):
                raise TypeError(f"Request key must be string, got {type(res).__name__}")
            if isinstance(amt, bool) or not isinstance(amt, (int, float)):
                raise TypeError(
                    f"Request at index {idx}, resource '{res}' must be a number, got {type(amt).__name__}"
                )
            if amt < 0 or math.isnan(amt) or math.isinf(amt):
                raise ValueError(f"Request at index {idx}, resource '{res}' has invalid amount: {amt}")

            if res not in resources:
                unknown_resource = True
            else:
                aggregated_demand[res] += amt

    if unknown_resource:
        return False

    # Empty requests / empty state: nothing is allocated, so valid.
    if not requests:
        return True

    # Capacity check
    for res, total in aggregated_demand.items():
        if total > resources[res]:
            return False

    # At least one resource must remain unallocated
    if resources and not any(aggregated_demand[r] < resources[r] for r in resources):
        return False

    return True
