from typing import Dict, List, Union
import math

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether the total requests fit within the available capacities.

    Args:
        resources: Mapping from resource name (cpu, ram, mem) to positive capacity.
        requests: List of mappings from resource name to a signed numeric amount.

    Returns:
        True if every requested resource exists and its total requested amount
        does not exceed capacity, including exact-capacity and empty allocations.
        False for invalid capacities, invalid requests, or exceeded capacities.

    Raises:
        ValueError: If inputs are not a dictionary of numeric capacities and a
            list of dictionaries of numeric request amounts with string keys.
    """
    if not isinstance(resources, dict):
        raise ValueError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise ValueError("Requests must be a list")

    # Validate the complete input format before checking allocation feasibility.
    for mapping in [resources] + requests:
        if not isinstance(mapping, dict):
            raise ValueError("Each request must be a dictionary")
        for key, value in mapping.items():
            if not isinstance(key, str):
                raise ValueError("Resource and request keys must be strings")
            if not isinstance(value, (int, float)):
                raise ValueError("Resource and request values must be numbers")

    resource_names = {"cpu", "ram", "mem"}
    for key, value in resources.items():
        if key not in resource_names or not math.isfinite(value) or value <= 0:
            return False

    usage: Dict[str, Number] = {}
    for request in requests:
        for key, value in request.items():
            if key not in resources or not math.isfinite(value):
                return False
            usage[key] = usage.get(key, 0) + value

    # Signed requests may offset earlier requests, so check only final totals.
    return all(amount <= resources[key] for key, amount in usage.items())
