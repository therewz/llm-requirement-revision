from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """Return whether total demand stays within each listed resource's capacity.

    Resource names are case-sensitive. Requests for resources not listed in
    resources are ignored, and capacities may be used exactly in full.
    Neither input is modified.
    """
    total_demand = {}
    for request in requests:
        for r_key, r_value in request.items():
            total_demand[r_key] = total_demand.get(r_key, 0) + r_value

    for r_key, r_capacity in resources.items():
        if total_demand.get(r_key, 0) > r_capacity:
            return False

    return True
