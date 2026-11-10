from typing import Dict, List, Union
from decimal import Decimal
from fractions import Fraction
from numbers import Real

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether total requests fit within the available capacities.

    Args:
        resources: Dictionary mapping resource names (cpu, ram, mem) to
            positive capacities.
        requests: List of dictionaries mapping resource names to signed
            numeric amounts. Amounts for each resource are summed.

    Returns:
        True if all requests are valid, no capacity is exceeded, and some
        capacity remains unallocated. Otherwise, False.

    Raises:
        ValueError: If inputs are not dictionaries/list of dictionaries with
            string keys and numeric values.
    """
    if not isinstance(resources, dict):
        raise ValueError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise ValueError("Requests must be a list")

    def validate_mapping(mapping):
        if not isinstance(mapping, dict):
            raise ValueError("Each request must be a dictionary")
        for key, value in mapping.items():
            if not isinstance(key, str):
                raise ValueError("Resource names must be strings")
            if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
                raise ValueError("Resource and request values must be numbers")

    # Validate the entire input format before checking allocation feasibility.
    validate_mapping(resources)
    for request in requests:
        validate_mapping(request)

    def exact_amount(value):
        try:
            # Treat floats as decimal quantities, avoiding rounding artifacts
            # such as 0.1 + 0.2 incorrectly exceeding a capacity of 0.3.
            return Fraction(str(value)) if isinstance(value, float) else Fraction(value)
        except (ValueError, OverflowError):
            # NaN and infinity are numeric, but are not valid capacities/requests.
            return None

    valid_names = {"cpu", "ram", "mem"}
    capacities = {}
    for key, value in resources.items():
        capacity = exact_amount(value)
        if key not in valid_names or capacity is None or capacity <= 0:
            return False
        capacities[key] = capacity

    usage = {key: Fraction(0) for key in capacities}
    for request in requests:
        for key, value in request.items():
            if key not in capacities:
                return False
            amount = exact_amount(value)
            if amount is None:
                return False
            usage[key] += amount

    # Signed requests can offset one another, so check final totals rather
    # than rejecting an intermediate total that exceeds capacity.
    if any(usage[key] > capacity for key, capacity in capacities.items()):
        return False

    # An empty resource mapping or an allocation consuming every capacity
    # cannot leave any resource capacity unallocated.
    return any(usage[key] < capacity for key, capacity in capacities.items())
