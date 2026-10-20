"""Private in-process CSV input view; every normal native validator still runs.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
import hashlib
from mta.serialization import canonical_parts
from pathlib import Path
import json
import io
import os


class JsonInputFile:
    """Private archived native JSON; no simultaneous bytes/text/graph copies.

    This is transport only. Every decode verifies all bytes and then runs the
    unchanged native validators; it never certifies calculation or admission.
    """
    def __init__(self, path):
        self.path = Path(path)

    def decode(self, expected, *, object_pairs_hook, parse_constant):
        checksum = hashlib.sha256()
        class HashedReader(io.RawIOBase):
            def readable(self):
                return True

            def readinto(self, buffer):
                count = stream.readinto(buffer)
                if count:
                    checksum.update(memoryview(buffer)[:count])
                return count

        with self.path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            with io.TextIOWrapper(io.BufferedReader(HashedReader()), encoding='utf-8') as text:
                value = json.load(text, object_pairs_hook=object_pairs_hook, parse_constant=parse_constant)
            observed = os.fstat(stream.fileno())
        after = self.path.stat()
        if checksum.hexdigest() != expected:
            raise ValueError('Daily operator input bytes differ')
        def identity(info):
            return info.st_size, info.st_mtime_ns, info.st_ino, info.st_dev
        if identity(before) != identity(observed) or identity(before) != identity(after):
            raise ValueError('Daily operator input changed during read')
        return value


class StreamedInput:
    def __init__(self, value, sha256):
        self._value = deepcopy(value)
        self.sha256 = sha256

    @classmethod
    def take(cls, value, sha256):
        """Transfer a CSV reader's exclusively owned graph, avoiding a copy.

        The public constructor and snapshot still isolate mutable callers.
        Only a producer relinquishing its local graph may use this boundary.
        """
        result = cls.__new__(cls)
        result._value, result.sha256 = value, sha256
        return result

    def snapshot(self, expected_sha256):
        value = self._checked(expected_sha256)
        return deepcopy(value)

    def _checked(self, expected_sha256):
        if self._value is None:
            raise ValueError('Input ownership was already transferred')
        checksum = hashlib.sha256()
        for part in canonical_parts(self._value, ensure_ascii=False):
            checksum.update(part)
        if expected_sha256 != self.sha256 or checksum.hexdigest() != expected_sha256:
            raise ValueError('Operator input bytes differ')
        return self._value

    def take_snapshot(self, expected_sha256):
        """Move the CSV reader's private graph to the one initialization owner."""
        value = self._checked(expected_sha256)
        self._value = None
        return value

    def __eq__(self, other):
        # Compatibility at command/test boundaries without encoding large inputs.
        if isinstance(other, bytes):
            import json
            return self._value == json.loads(other)
        return self is other
