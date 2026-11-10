from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Check total demand against each available resource's capacity.

    Resource names are case-sensitive. Requests for resources not present in
    resources do not constrain feasibility. At least one available resource
    must have unused capacity after allocation. Inputs are not modified.
    """
    total_demand = {}
    for request in requests:
        for r_key, r_value in request.items():
            total_demand[r_key] = total_demand.get(r_key, 0) + r_value

    for r_key, r_capacity in resources.items():
        if total_demand.get(r_key, 0) > r_capacity:
            return False

    return any(
        total_demand.get(r_key, 0) < r_capacity
        for r_key, r_capacity in resources.items()
    )
