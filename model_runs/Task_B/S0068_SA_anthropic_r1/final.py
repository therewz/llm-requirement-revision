from typing import Dict, List, Union
import math
import numbers

Number = Union[int, float]


def _check_number(value, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise TypeError(f"{label} must be a number, got {type(value).__name__}")
    if math.isnan(value) or value < 0:
        raise ValueError(f"{label} has invalid value: {value}")


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests can be satisfied simultaneously: for every
    resource, the summed demand across all requests must not exceed capacity
    (demand equal to capacity is fine).

    - Resource names are case-sensitive.
    - A request referencing a resource not in `resources` makes the result False.
    - Empty requests (or empty resources with empty requests) are feasible.
    - Inputs are validated fully before evaluation and never mutated.

    Raises:
        TypeError: For invalid types (non-numeric, booleans, non-string keys)
        ValueError: For negative or NaN values
    """
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, (list, tuple)):
        raise TypeError("Requests must be a list")

    for r, cap in resources.items():
        if not isinstance(r, str):
            raise TypeError(f"Resource key must be string, got {type(r).__name__}")
        _check_number(cap, f"Resource '{r}'")

    # Validate every request before deciding (atomic processing)
    for idx, req in enumerate(requests):
        if not isinstance(req, dict):
            raise TypeError(f"Request at index {idx} is not a dictionary")
        for res, amt in req.items():
            if not isinstance(res, str):
                raise TypeError(f"Request key must be string, got {type(res).__name__}")
            _check_number(amt, f"Request at index {idx}, resource '{res}'")

    demand: Dict[str, Number] = {}
    unknown = False
    for req in requests:
        for res, amt in req.items():
            if res not in resources:
                unknown = True
                continue
            demand[res] = demand.get(res, 0) + amt

    if unknown:
        return False

    return all(total <= resources[res] for res, total in demand.items())
