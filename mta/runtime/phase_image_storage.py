"""Explicit same-phase physical references; not business or phase acceptance.

This writer is activated only with the versioned phase contract. A content match
alone cannot create a source relationship. Every alias below is a qualified
projection with a specific logical owner, including empty populations.
"""
from mta.runtime import relational_state as typed
from mta.runtime.phase_state_layout import REGISTRY

FORMAT = 'fresh-phase-image-references-v2'
IDENTITY_FIELDS = ('table', 'count', 'digest', 'fields')
CONTROL_PROJECTIONS = {
    'SuggestionsLog': 'suggestions_log',
    'OrderDataSummary': 'order_summary',
}


def source_path(path):
    """A finite producer relationship, never an arbitrary same-table lookup."""
    parts = path.split('/')
    if len(parts) == 4 and parts[:3] == ['phase', 'DBM', 'dbm']:
        control = CONTROL_PROJECTIONS.get(parts[3])
        return None if control is None else 'phase/DBM/controls/'+control
    if (len(parts) == 5 and parts[:3] == ['phase', 'DBM', 'report-facts']
            and parts[3] in typed.REPORT_STAGES
            and 'closing/dbm/'+parts[4] in typed.CATALOG['bindings']):
        return 'phase/DBM/dbm/'+parts[4]
    return None


class ImageWriter:
    """One synchronous encode call; no global cache or object-identity trust.

    Every input still receives the complete typed ordered description. Reuse
    reduces physical writes only; it does not claim incremental hashing/reads.
    """
    def __init__(self, writer, *, parent_manifest=None):
        self.writer = writer
        self.parent = parent_manifest
        self.images = {}

    def __call__(self, path, table, rows):
        columns = {name.casefold(): (name, kind) for name, kind in REGISTRY[table]}
        description = typed.describe_rows(rows, columns, path)
        meta = dict(description[0], table=table)
        inherited = None if self.parent is None else self.parent['images'].get(
            'phase/'+self.parent['phase']+'/'+path.split('/', 2)[2])
        same_phase = self.images.get(source_path(path))
        # Corresponding-path ancestry stays preferred. Both candidate kinds
        # require the actual producer's complete ordered typed equality.
        for candidate in (inherited, same_phase):
            if candidate is not None and all(meta[k] == candidate[k] for k in IDENTITY_FIELDS):
                self.images[path] = candidate
                return candidate
        result = self.writer(path, table, rows, description)
        self.images[path] = result
        return result


def owns_physical_image(manifests, logical_image, metadata):
    """Authenticate corresponding ancestry or a declared v2 logical projection.

    Manifests must already have passed their phase/run/input/action acceptance
    checks. This function adds no admission authority and never loads rows.
    """
    current = manifests[0]
    if current['images'].get(logical_image) != metadata:
        return False
    if not logical_image.startswith('phase/'+current['phase']+'/'):
        return False
    suffix = logical_image.split('/', 2)[2]
    for owner in manifests:
        candidate = 'phase/'+owner['phase']+'/'+suffix
        if metadata.get('image') == candidate and owner['images'].get(candidate) == metadata:
            return True
    if current.get('storage_format') != FORMAT:
        return False
    source = source_path(logical_image)
    if source is None or current['images'].get(source) != metadata:
        return False
    parts = source.split('/')
    section = {'controls': 'control_final', 'dbm': 'final_dbm'}[parts[2]]
    binding = 'closing/'+parts[2]+'/'+parts[3]
    if metadata.get('table') != '/'.join(typed.CATALOG['bindings'][binding]):
        return False
    if current.get('state', {}).get(section, {}).get(parts[3]) != {'image': source}:
        return False
    # The declared graph has at most report -> DBM -> control -> ancestor;
    # source_path cannot create a cycle or cross to an unrelated population.
    return owns_physical_image(manifests, source, metadata)
