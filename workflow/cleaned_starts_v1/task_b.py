"""Project S0027's Phase-II feasibility decision to the common Boolean API."""

from hashlib import sha256


_S0027_PHASE_II_SHA256 = '07f5d56a0ecea4b5e13ddd660b01437c61b033500aa6a57ff97e31d3398e08b5'


def clean(participant_id: str, source: bytes, selected_profile: str) -> tuple[bytes, list[str]]:
    """Return a derivative of the inspected source without changing its decision logic."""
    if participant_id != 'S0027':
        return source, []
    if sha256(source).hexdigest() != _S0027_PHASE_II_SHA256:
        raise ValueError('S0027 source differs from the reviewed Phase-II artifact')

    replacements = (
        (b'from typing import Dict, List, Union, Tuple', b'from typing import Dict, List, Union'),
        (b') -> Tuple[bool, Dict[str, Number]]:', b') -> bool:'),
        (
            b'        Tuple[bool, Dict[str, Number]] - \n'
            b'            - True if the allocation is feasible and at least one resource remains.\n'
            b'            - False otherwise.\n'
            b'            - Dictionary of remaining resources after allocation attempt.',
            b'        True if the allocation is feasible and at least one resource remains.\n'
            b'        False otherwise.',
        ),
        (b'return False, resources', b'return False'),
        (b'return False, remaining_resources', b'return False'),
        (b'return True, remaining_resources', b'return True'),
    )
    for before, after in replacements:
        source = source.replace(before, after)
    return source, ['Standardize the public return to the existing Boolean feasibility decision.']
