from typing import Dict, List, Union
import math

Number = Union[int, float]


def _check_number(value, what: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{what} must be numbers.")
    if math.isnan(value) or math.isinf(value) or value < 0:
        raise ValueError(f"{what} must be non-negative finite numbers.")


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    # ----------------------
    # VALIDATION
    # ----------------------
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary.")
    if not isinstance(requests, list):
        raise TypeError("Requests must be provided as a list of dictionaries.")

    for r_key, r_val in resources.items():
        if not isinstance(r_key, str):
            raise TypeError("Resource keys must be strings.")
        _check_number(r_val, "Resource values")

    undefined_reference = False
    for req in requests:
        if not isinstance(req, dict):
            raise ValueError("Each request must be a dictionary.")
        for req_key, req_val in req.items():
            if not isinstance(req_key, str):
                raise TypeError("Request keys must be strings.")
            _check_number(req_val, "Request values")
            if req_key not in resources:
                undefined_reference = True

    # Requests for undefined resources can never be satisfied.
    if undefined_reference:
        return False

    # ----------------------
    # AGGREGATE REQUESTS
    # ----------------------
    total_requested = {res: 0 for res in resources}
    for req in requests:
        for key, val in req.items():
            total_requested[key] += val

    # ----------------------
    # CHECK FEASIBILITY (each resource enforced independently, all together)
    # ----------------------
    for res, total in total_requested.items():
        if total > resources[res]:
            return False

    return True
