from typing import Dict, List, Union

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether a set of resource requests can be satisfied given limited capacities.

    Args:
        resources : Dict[str, Number], Mapping from resource name to total available capacity.
        requests : List[Dict[str, Number]], List of requests. Each request is a mapping from resource name to the amount required.

    Returns:
        True if the allocation is feasible, False otherwise.
    """
    # Validate inputs
    if not confirm_type_of_key_and_value(resources, str, Number):
        raise ValueError("Invalid type in resources dictionary")
    
    for i, request in enumerate(requests):
        if request is None or not isinstance(request, dict):
            return False
        if not confirm_type_of_key_and_value(request, str, Number):
            raise ValueError(f"Invalid type in requests list at index {i}")
    
    # Compute total requests per resource
    total_requests = build_total_request(requests)
    
    # Every requested resource must fit within its available capacity.
    for key, requested in total_requests.items():
        if requested > resources.get(key, 0):
            return False
    
    return True

def confirm_type_of_key_and_value(dictionary, expected_key_type, expected_value_type):
    for key in dictionary:
        if not isinstance(key, expected_key_type) or not isinstance(dictionary[key], expected_value_type):
            return False
    return True

def build_total_request(requests):
    total_requests = {}
    for request in requests:
        for key, value in request.items():
            total_requests[key] = total_requests.get(key, 0) + value
    return total_requests