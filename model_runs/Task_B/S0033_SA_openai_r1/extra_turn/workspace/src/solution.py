from typing import Dict, List, Union
from fractions import Fraction
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether the total requests fit within the available capacities.

    Args:
        resources: Dictionary mapping "cpu", "ram", or "mem" to positive capacities.
        requests: List of dictionaries mapping resource names to signed amounts.

    Returns:
        True if all requests are valid and their totals do not exceed capacity,
        including exact-capacity allocations and an empty request list. Invalid
        capacities, invalid numeric requests, and missing resources return False.

    Raises:
        ValueError: If inputs are not dictionaries/list of dictionaries with
            string keys and numeric values.
    """
    if not isinstance(resources, dict):
        raise ValueError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise ValueError("Requests must be a list")

    # Validate the entire input format before assessing feasibility.
    def validate_mapping(mapping: Dict[str, Number]) -> None:
        if not isinstance(mapping, dict):
            raise ValueError("Each request must be a dictionary")
        for key, value in mapping.items():
            if not isinstance(key, str):
                raise ValueError("Resource and request keys must be strings")
            if not isinstance(value, (int, float)):
                raise ValueError("Resource and request values must be numbers")

    validate_mapping(resources)
    for request in requests:
        validate_mapping(request)

    def exact_amount(value: Number) -> Fraction:
        # Preserve decimal amounts without introducing a capacity tolerance.
        return Fraction(str(value)) if isinstance(value, float) else Fraction(value)

    allowed_resources = {"cpu", "ram", "mem"}
    capacities: Dict[str, Fraction] = {}
    for key, capacity in resources.items():
        if key not in allowed_resources or capacity <= 0:
            return False
        if isinstance(capacity, float) and not math.isfinite(capacity):
            return False
        capacities[key] = exact_amount(capacity)

    usage: Dict[str, Fraction] = {}
    for request in requests:
        for key, amount in request.items():
            if key not in resources:
                return False
            if isinstance(amount, float) and not math.isfinite(amount):
                return False
            usage[key] = usage.get(key, Fraction(0)) + exact_amount(amount)

    # Negative requests can offset earlier positive requests, so compare only
    # after all requests have been accumulated.
    return all(usage.get(key, 0) <= capacity for key, capacity in capacities.items())
