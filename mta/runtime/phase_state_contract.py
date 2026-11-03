"""Phase layout compatibility is separate from physical implementation identity.

This is not native-release or frozen-request admission. Those owners still
authenticate the original capture, executable producers, registration and role.
Old immutable snapshots have no independent logical-contract field, so exactly
one qualified legacy codec is interpreted here. Unknown old recipes refuse.
"""
import inspect
import re

from mta.serialization import digest

SCHEMA = 'fresh-native-phase-logical-contract-v1'
LEGACY_RECIPE = '2b307bcb0cad7f75cf0f2273938cd072fb4b25fe1191252691cb6e113873fc7c'
LEGACY_LOGICAL = '938547791982517980a4febf79022f299645040f0e41a364b49db70c1d73b774'


def logical_digest():
    """Logical graph and dispatch, excluding physical placement.

Imported business-rule bodies are not covered by this descriptor. Release
qualification must establish their compatibility; this is not a substitute
for business-rule versioning or end-to-end continuation proofs.
"""
    from mta.runtime import phase_state_layout
    from mta.temporal import chain, day_phases
    return digest(dict(layout=inspect.getsource(phase_state_layout),
        chain=inspect.getsource(chain), phases=inspect.getsource(day_phases),
        registry=phase_state_layout.REGISTRY))


def describe():
    return dict(schema=SCHEMA, digest=logical_digest())


def effective(recipe, manifest):
    """Interpret a sealed descriptor; caller retains all owner/integrity checks."""
    from mta.runtime.phase_image_storage import READABLE_FORMATS, supports_inherited_images
    if (type(recipe) is not str or re.fullmatch('[0-9a-f]{64}', recipe) is None
            or type(manifest) is not dict
            or manifest.get('schema') != 'fresh-native-phase-state-v1'
            or not supports_inherited_images(manifest)):
        raise ValueError('Phase contract descriptor differs')
    if 'phase_contract' not in manifest:
        if recipe != LEGACY_RECIPE or 'storage_format' in manifest:
            raise ValueError('Unknown legacy phase implementation')
        return LEGACY_LOGICAL
    contract = manifest['phase_contract']
    if (recipe == LEGACY_RECIPE or type(contract) is not dict
            or set(contract) != {'schema', 'digest'} or contract.get('schema') != SCHEMA
            or type(contract.get('digest')) is not str
            or re.fullmatch('[0-9a-f]{64}', contract['digest']) is None
            or manifest.get('storage_format') not in READABLE_FORMATS):
        raise ValueError('Unknown phase logical or storage contract')
    return contract['digest']


def compatible(snapshot):
    try:
        return effective(snapshot.recipe_digest, snapshot.manifest) == logical_digest()
    except (TypeError, ValueError):
        return False


def require(snapshot):
    if not compatible(snapshot):
        raise ValueError('Phase logical execution contract differs')
