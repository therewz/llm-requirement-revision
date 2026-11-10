from typing import Dict, List, Union
import math

Number = Union[int, float]


def _is_number(val) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def is_allocation_feasible(
    resources: Dict[str, Number],
    requests: List[Union[Dict[str, Number], List[Dict[str, Number]]]]
) -> bool:
    """Return True if every request can be satisfied simultaneously.

    A request is either a dict {resource: amount} (a single option) or a
    list/tuple of such dicts (alternative options; exactly one is chosen).
    A request is satisfied fully by one option or not at all. Options using
    unknown resource types or invalid (negative / non-numeric) amounts are
    not valid options. Total usage of each resource must not exceed capacity.
    """
    if resources is None or requests is None:
        raise TypeError("Resources and requests cannot be None")
    if not isinstance(resources, dict):
        raise TypeError("Resources must be a dictionary")

    for val in resources.values():
        if not _is_number(val):
            raise TypeError("Resource values must be numbers")
        if math.isnan(val) or val < 0:
            raise ValueError("Resource capacities must be non-negative")

    def valid_option(opt):
        if not isinstance(opt, dict):
            return None
        cleaned = {}
        for key, val in opt.items():
            if key not in resources or not _is_number(val):
                return None
            if math.isnan(val) or val < 0 or math.isinf(val):
                return None
            if val > 0:
                cleaned[key] = val
        # An option that alone exceeds capacity can never be used
        for key, val in cleaned.items():
            if val > resources[key]:
                return None
        return cleaned

    all_options = []
    for req in requests:
        raw = list(req) if isinstance(req, (list, tuple)) else [req]
        options = []
        for opt in raw:
            cleaned = valid_option(opt)
            if cleaned is not None and cleaned not in options:
                options.append(cleaned)
        if not options:
            return False  # request cannot be satisfied
        all_options.append(options)

    # Most constrained requests first
    all_options.sort(key=len)
    remaining = dict(resources)
    n = len(all_options)

    def solve(i: int) -> bool:
        if i == n:
            return True
        for opt in all_options[i]:
            if all(remaining[k] >= v for k, v in opt.items()):
                for k, v in opt.items():
                    remaining[k] -= v
                ok = solve(i + 1)
                for k, v in opt.items():
                    remaining[k] += v
                if ok:
                    return True
        return False

    return solve(0)
