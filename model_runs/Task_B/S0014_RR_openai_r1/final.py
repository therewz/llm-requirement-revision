from typing import Dict, List, Union

Number = Union[int, float]

def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Dict[str, Number]]
) -> bool:
    """
    Determine whether all requests fit while leaving some capacity unallocated.

    Args:
        resources: Mapping from resource name to total available capacity.
        requests: List of mappings from resource name to the amount required.

    Returns:
        True if every request can be satisfied and at least one resource has
        capacity remaining, False otherwise. Missing resources have zero capacity.
    """
    total_requests = build_total_request(requests)

    # Every requested resource must have enough capacity, including resources
    # that are absent from the available-resource mapping.
    for key, requested in total_requests.items():
        if requested > resources.get(key, 0):
            return False

    has_free_resource = False
    for key, available in resources.items():
        requested = total_requests.get(key, 0)
        if requested > available:
            return False
        if requested < available:
            has_free_resource = True

    return has_free_resource

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
