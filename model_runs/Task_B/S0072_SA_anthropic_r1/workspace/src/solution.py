from typing import Dict, List, Union
import math

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determines if a set of resource requests can be satisfied
    given the available resources.

    Args:
        resources (Dict[str, Number]): Available resources {resource_name: capacity}.
        requests (List[Dict[str, Number]]): List of resource requests.

    Returns:
        bool: True if all requests can be fully satisfied without exceeding the
              capacity of any resource. False otherwise. Inputs are not modified.

    Raises:
        TypeError: If input types are invalid.
        ValueError: If any resource or request has invalid numeric values.
    """
    # Type checks
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")
    if not isinstance(requests, list):
        raise TypeError("Requests must be a list")

    for res_key, res_val in resources.items():
        if not isinstance(res_key, str):
            raise TypeError(f"Resource keys must be strings, got {type(res_key).__name__}")
        if not isinstance(res_val, (int, float)):
            raise TypeError(f"Resource values must be numeric, got {type(res_val).__name__}")
        if math.isnan(res_val) or math.isinf(res_val) or res_val < 0:
            raise ValueError(f"Invalid resource value for '{res_key}': {res_val}")

    total_requested = {res: 0 for res in resources}
    feasible = True

    for idx, req in enumerate(requests):
        if not isinstance(req, dict):
            raise TypeError(f"Request at index {idx} must be a dictionary")
        for req_key, req_val in req.items():
            if not isinstance(req_key, str):
                raise TypeError(f"Request keys must be strings, got {type(req_key).__name__}")
            if not isinstance(req_val, (int, float)) or isinstance(req_val, bool):
                raise TypeError(f"Request values must be numeric, got {type(req_val).__name__}")
            if math.isnan(req_val) or math.isinf(req_val) or req_val < 0:
                raise ValueError(f"Invalid request value for '{req_key}' in request {idx}: {req_val}")
            if req_key not in resources:
                # A positive demand for a resource that does not exist cannot be met.
                if req_val > 0:
                    feasible = False
                continue
            total_requested[req_key] += req_val

    if not feasible:
        return False

    # No resource may be over-allocated (exactly using full capacity is allowed)
    for res, total in total_requested.items():
        if total > resources[res]:
            return False

    return True
