"""One operation-local owner of authenticated, validated native daily input.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

This is not a process cache or an admission bypass. Only the native intake
gates can produce an instance. Persisted preparation is a separate, revision-
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
    from mta.application.streamed_input import StreamedInput
    if isinstance(raw, StreamedInput) and getattr(raw, '_csv_native_rows', None) is not None:
        return _prepare_csv(raw, input_sha256, raw._csv_native_rows)
    from mta.runtime.production_daily import decode
    return PreparedDaily(_ISSUER, decode(raw, input_sha256), input_sha256)


def _prepare_csv(carrier, input_sha256, parsed_rows):
    """Finish the parser-owned gate; canonical archive bytes were just hashed."""
    from mta.application.production_csv import _CsvNativeRows
    if type(parsed_rows) is not _CsvNativeRows:
        raise ValueError('Native CSV evidence requires its parser')
    from mta.runtime.production_daily import _decode_csv_value
    value = parsed_rows._handoff(carrier, input_sha256)
    result = PreparedDaily(_ISSUER, _decode_csv_value(value, parsed_rows), input_sha256)
    carrier._value = None
    parsed_rows._release()
    return result


def restored(value, input_sha256, admission):
    """Private accepted-batch caller; its sealed rows were validated at intake."""
    result = PreparedDaily(_ISSUER, value, input_sha256)
    result.admission = admission
    return result
