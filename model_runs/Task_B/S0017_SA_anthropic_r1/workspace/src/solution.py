from typing import Dict, List, Union

Number = Union[int, float]


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Returns True if, for every resource, the total demand across all requests
    does not exceed the available capacity.
    """

    # Error checking
    if not isinstance(resources, dict):
        raise ValueError("Undefined Resource!")

    for req in requests:
        if not isinstance(req, dict):
            raise ValueError("Not a Dictionary!")

    total_demand: Dict[str, float] = {}

    # Calculate total demand
    for i, req in enumerate(requests, 1):
        for res_name, amount in req.items():
            if res_name not in resources:
                return False
            try:
                amount = float(amount)
            except (TypeError, ValueError):
                raise ValueError(
                    f"Invalid numeric value for resource '{res_name}' "
                    f"in request #{i}: {amount!r}"
                )
            if amount < 0:
                raise ValueError(
                    f"Negative value not allowed for resource '{res_name}' "
                    f"in request #{i}: {amount}"
                )

            total_demand[res_name] = total_demand.get(res_name, 0.0) + amount

    # Check feasibility against capacities
    for res_name, available in resources.items():
        if total_demand.get(res_name, 0.0) > float(available):
            return False

    return True
