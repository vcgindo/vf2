"""Supply immutable image-owned configuration to unchanged native admission.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import json
import os
from pathlib import Path
import re
import sys


def configure(path=Path('/opt/vectorflow/release.json'), environ=None):
    environ = os.environ if environ is None else environ
    identity = json.loads(Path(path).read_text())
    values = {'VF_NATIVE_RELEASE_COMMIT': ('source_commit', 40),
              'VF_NATIVE_RELEASE_SHA256': ('native_sha256', 64),
              'VF_SOURCE_MANIFEST_SHA256': ('source_sha256', 64)}
    for name, (field, length) in values.items():
        value = identity[field]
        if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{' + str(length) + '}', value):
            raise ValueError('Invalid baked image identity: ' + field)
        if environ.get(name) not in (None, '', 'image', value):
            raise ValueError('Configured identity differs from this image: ' + name)
    for name, (field, _) in values.items():
        environ[name] = identity[field]
    return identity


if __name__ == '__main__':
    configure()
    from release.native_identity import require_current
    require_current()  # Complete existing native file/manifest validation, before any DB operation.
    arguments = sys.argv[1:]
    if not arguments:
        raise ValueError('Explicit service or operator command required')
    if arguments[0] in ('-', '-m') or arguments[0].endswith('.py'):
        arguments.insert(0, 'python')
    os.execvp(arguments[0], arguments)
