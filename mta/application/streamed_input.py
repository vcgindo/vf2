"""Private in-process CSV input view; every normal native validator still runs.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
import hashlib
from mta.serialization import canonical_parts


class StreamedInput:
    def __init__(self, value, sha256):
        self._value = deepcopy(value)
        self.sha256 = sha256

    def snapshot(self, expected_sha256):
        checksum = hashlib.sha256()
        for part in canonical_parts(self._value, ensure_ascii=False):
            checksum.update(part)
        if expected_sha256 != self.sha256 or checksum.hexdigest() != expected_sha256:
            raise ValueError('Operator input bytes differ')
        return deepcopy(self._value)

    def __eq__(self, other):
        # Compatibility at command/test boundaries without encoding large inputs.
        if isinstance(other, bytes):
            import json
            return self._value == json.loads(other)
        return self is other
