"""Check whether resource requests fit within the available capacities."""

from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all resource requests can be satisfied in full.

    Args:
        resources : Dict[str, Number]
            Mapping from resource name to available integer capacity,
            between 0 and 70 inclusive.
        requests : List[Dict[str, Number]]
            List of requests mapping resource names to nonnegative
            integer amounts. Floats and booleans are not valid counts.

    Returns:
        True if every request is valid and cumulative demand for each
        resource fits its capacity, False otherwise.
    """

    # Validate resource capacities.
    for capacity in resources.values():
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            return False
        if not 0 <= capacity <= 70:
            return False

    # Units allocated to one request cannot be reused for another.
    total_requested: Dict[str, Number] = {r: 0 for r in resources}

    for request in requests:
        for resource, amount in request.items():
            if resource not in resources:
                return False

            if not isinstance(amount, int) or isinstance(amount, bool):
                return False
            if amount < 0:
                return False

            total_requested[resource] += amount
            if total_requested[resource] > resources[resource]:
                return False

    return True
