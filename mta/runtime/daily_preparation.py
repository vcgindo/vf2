"""One operation-local owner of authenticated, validated native daily input.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

This is not a process cache or an admission bypass. Only the existing native
decoder can produce an instance. Persisted preparation is a separate, revision-
checked boundary; this object cannot be constructed from a caller's metadata.
"""
from mta.mdm.initialization_contract import sha

_ISSUER = object()


class PreparedDaily:
    def __init__(self, issuer, value, input_sha256):
        if issuer is not _ISSUER:
            raise ValueError('Native daily decoder must own preparation')
        self._value = value
        self.sha256 = sha(input_sha256, 'daily input')
        self.admission = None

    def checked(self, expected_sha256):
        if self._value is None or expected_sha256 != self.sha256:
            raise ValueError('Native daily preparation identity differs')
        return self._value

    def release(self):
        self._value = None


def prepare(raw, input_sha256):
    if isinstance(raw, PreparedDaily):
        raw.checked(input_sha256)
        return raw
    from mta.runtime.production_daily import decode
    return PreparedDaily(_ISSUER, decode(raw, input_sha256), input_sha256)


def restored(value, input_sha256, admission):
    """Private accepted-batch caller; its sealed rows were validated at intake."""
    result = PreparedDaily(_ISSUER, value, input_sha256)
    result.admission = admission
    return result
