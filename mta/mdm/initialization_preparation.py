"""One private preparation owner for initialization, never a validator bypass.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from mta.serialization import digest

_OWNER = object()


class PreparedInitialization:
    __slots__ = ('_decoded','_pins','_claimed','report','content_digest','families')

    def __init__(self, key, decoded, pins, report):
        if key is not _OWNER:
            raise ValueError('Initialization must come from the preparation owner')
        self._decoded, self._pins, self._claimed = decoded, pins, False
        self.report = report
        from mta.mdm.initialization import families_for
        self.content_digest = digest(decoded[1])
        self.families = families_for(decoded[2])

    @property
    def sha256(self):
        return self._pins[0]

    def claim(self, sha256, configuration, recipe):
        if self._claimed or self._pins != (sha256,configuration,recipe):
            raise ValueError('Prepared initialization identity differs or is already consumed')
        self._claimed = True
        decoded, self._decoded = self._decoded, None
        return decoded


def prepare(raw, sha256, *, expected_configuration, expected_recipe):
    from mta.runtime.production_preflight import Requirements, parse, initialization_value, require
    c = Requirements('installation')
    from mta.application.streamed_input import StreamedInput
    value = raw.take_snapshot(sha256) if type(raw) is StreamedInput else parse(raw,sha256,c,'/input')
    report, decoded = initialization_value(value,c,expected_configuration=expected_configuration,
        expected_recipe=expected_recipe)
    require(report,'installation')
    if decoded is None:
        raise ValueError('Initialization has no complete validated value')
    # The original envelope is no longer needed; keep only normalized owners.
    return PreparedInitialization(_OWNER,(None,decoded[1],decoded[2]),
        (sha256,expected_configuration,expected_recipe),report)
