from typing import Dict, List, Union
from collections import Counter

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Args:
        resources : Dict[str, Number]
            Mapping from resource name to total available capacity.
        requests : List[Dict[str, Number]]
            List of requests. Each request is a mapping from resource name to the amount required.

    Returns:
        bool
            True if the total demand for every resource is within its capacity,
            False otherwise.
    """
    total_requests: Counter = Counter()
    for req in requests:
        for res, count in req.items():
            total_requests[res] += count

    for res, total in total_requests.items():
        if total > resources.get(res, 0):
            return False
    return True
