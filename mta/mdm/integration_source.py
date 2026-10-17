# **DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""Explicit combined ownership seal; never an installer or acceptance issuer.

Historical root and family receipts stay immutable. The new seal describes only
owners already installed on that same source and one accepted own predecessor.
"""
import hashlib
from pathlib import Path

from django.db import transaction
from mta.mdm.daily_source import (FORCE_SCHEMA, SEASON_SCHEMA,
                                 require_root)
from mta.runtime.mdm_models import MdmFamilySource, MdmSource
from mta.runtime.mdm_integration_models import MdmSourceIntegration
from mta.serialization import digest

SCHEMA = 'fresh-mdm-source-integration-v1'
DAILY_OWNER_SCHEMA = 'fresh-mdm-accepted-closing-owner-v1'
CONFIGURATIONS = {
    1: 'mdm_sku.json', 2: 'mdm_location.json', 3: 'mdm_skuloc.json',
    4: 'mdm_sob.json', 5: 'mdm_moq.json', 6: 'mdm_stop_pipo.json',
    7: 'mdm_phase_controls.json', 8: 'mdm_phase_controls.json',
    9: 'mdm_phase_controls.json', 10: 'mdm_season.json',
    11: 'mdm_season.json', 12: 'mdm_season.json', 13: 'mdm_force.json',
}
CAPTURES = {'supplier': {4, 5}, 'force': {13}, 'season': {10, 11, 12},
            'stop_pipo': {6}, 'phase_controls': {7, 8, 9}}


def adapter_digest():
    root = Path(__file__).resolve().parents[1]
    paths = ['mdm/' + name + '.py' for name in (
        'integration_source', 'source', 'daily_source', 'daily_source_install', 'owned_namespace',
        'families', 'drafts', 'daily_input', 'supplier_source', 'force_source',
        'season_source', 'stop_pipo_source', 'phase_controls_source')]
    paths += ['mdm/' + family + '_' + suffix + '.py'
              for family in ('supplier', 'force', 'season', 'stop_pipo', 'phase_controls')
              for suffix in ('capture', 'revisions')]
    paths += ['runtime/' + name + '.py' for name in (
        'temporal', 'services', 'input_storage', 'input_tables', 'mdm_integration_models')]
    paths += ['presentation/mdm_views.py', 'presentation/context.py']
    return digest({name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                   for name in paths})


def configuration_digest(ids):
    root = Path(__file__).resolve().parents[1] / 'config'
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in sorted({CONFIGURATIONS[mid] for mid in ids})}


def owner_identity(source):
    """Read actual complete owners, without claiming publication eligibility."""
    base = require_root(source, artifact_sha256=source.receipt.get('artifact_sha256'),
                        artifact_schema=source.receipt.get('artifact_schema'))
    rows = {row.master_id: row for row in MdmFamilySource.objects.filter(source=source)}
    ids = {1, *rows}
    if (1 in rows or not {1, 2, 3} <= ids or ids - set(CONFIGURATIONS)
            or any((ids & group) not in (set(), group)
                   for group in ({4, 5}, {7, 8, 9}, {10, 11, 12}))):
        raise ValueError('Combined MDM requires base1–3 and complete shared owner groups')
    # Original fixture schema prerequisites remain; no conversion of a Force or
    # Season root into an unrelated family opening is permitted.
    if (source.receipt['schema'] == FORCE_SCHEMA and 13 not in ids
            or source.receipt['schema'] == SEASON_SCHEMA and 10 not in ids):
        raise ValueError('Combined MDM original root family is absent')
    result = {'1': digest(base['1'])}
    for mid in (2, 3):
        row = rows[mid]
        if row.receipt != base[str(mid)] or row.digest != digest(row.receipt):
            raise ValueError('Combined MDM base owner identity differs')
    if 4 in ids:
        from mta.mdm.supplier_source import require_installed
        for mid in (4, 5):
            require_installed(source, mid)
    for key, module in ((6, 'stop_pipo'), (7, 'phase_controls'),
                        (10, 'season'), (13, 'force')):
        if key in ids:
            from importlib import import_module
            owner = import_module('mta.mdm.' + module + '_source').require_installed(source)
            if key in (10, 13) and owner.provenance.get('artifact_sha256') != source.receipt['artifact_sha256']:
                raise ValueError('Combined MDM family artifact differs from its root')
            scoped_fields = {10: ('supplement',),
                             13: ('fixture_override', 'hierarchy_supplement')}.get(key, ())
            if any(owner.provenance.get(name) != source.receipt.get(name) for name in scoped_fields):
                raise ValueError('Combined MDM cannot transfer a family fixture approval to another root')
    for mid, row in rows.items():
        if not isinstance(row.receipt, dict) or row.digest != digest(row.receipt):
            raise ValueError('Combined MDM family receipt differs')
        result[str(mid)] = row.digest
    return result


def installed_binding(source):
    """An existing seal is mandatory evidence, never an optional failed check."""
    seal = MdmSourceIntegration.objects.filter(source=source).first()
    if seal is None:
        return None
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    if source.receipt.get('schema') == SOURCE_SCHEMA:
        from mta.mdm.production_families import require_binding
        return require_binding(source)
    p = seal.receipt
    family_digests = owner_identity(source)
    if (not isinstance(p, dict) or p.get('schema') != SCHEMA
            or p.get('source_digest') != source.digest
            or p.get('families') != family_digests
            or p.get('adapter_sha256') != adapter_digest()
            or p.get('configuration') != configuration_digest({int(mid) for mid in family_digests})
            or digest(p) != seal.digest):
        raise ValueError('Combined MDM integration identity differs')
    if p.get('required_families') is not None and (
            p['required_families'] != list(range(1, 14))
            or set(family_digests) != {str(i) for i in p['required_families']}):
        raise ValueError('Complete MDM integration roster differs')
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    anchor = MdmDailyInputCapture.objects.select_related('run').filter(
        source=source, run_id=p.get('run_id'), status='CONSUMED').first()
    if (anchor is None or anchor.run.status != 'SUCCEEDED'
            or anchor.run.output_digest != p.get('output_digest')
            or anchor.revision_digest != p.get('capture_digest')):
        raise ValueError('Combined MDM integration anchor differs')
    return seal


def require_unsealed(source):
    if MdmSourceIntegration.objects.filter(source=source).exists():
        raise ValueError('Combined MDM roster is sealed; additional installation is prohibited')


def accepted_closing(source, run, family_ids):
    """Lock and read one accepted own closing for additive family onboarding.

    Callers own the atomic transaction. This neither creates a capture nor
    grants acceptance: selected_run and the immutable consumed input prove it.
    """
    from mta.mdm.daily_source import require_binding
    from mta.mdm.supplier_revisions import lock_transaction
    from mta.presentation.context import selected_run
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.validation_storage import read_input
    from mta.runtime.services import read_outputs
    lock_transaction(source.pk)
    source = MdmSource.objects.select_for_update().get(pk=source.pk)
    require_unsealed(source)
    require_binding(source, artifact_sha256=source.receipt['artifact_sha256'],
                    artifact_schema=source.receipt['artifact_schema'])
    if selected_run().pk != run.pk:
        raise ValueError('Family binding requires the explicit accepted selected publication')
    anchor = current_capture(source, run)
    if (MdmFamilySource.objects.filter(source=source, master_id__in=family_ids).exists()
            or MdmDailyInputCapture.objects.filter(source=source, status='CAPTURED',
                                                   retries__isnull=True).exists()):
        raise ValueError('Family binding requires absent owners and no pending capture')
    snapshot = read_input(run, components=('mdm_input',)).get('mdm_input')
    if (not snapshot or snapshot.get('source_id') != source.pk
            or snapshot.get('source_digest') != source.digest
            or snapshot.get('revision_digest') != anchor.revision_digest):
        raise ValueError('Family binding accepted input belongs to a different source')
    closing = read_outputs(run)['ClosingState'][0]
    provenance = dict(schema=DAILY_OWNER_SCHEMA, source_digest=source.digest,
        artifact_sha256=source.receipt['artifact_sha256'], dll_sha256=source.dll_digest,
        run_id=str(run.pk), output_digest=run.output_digest,
        capture_digest=anchor.revision_digest, root_state_digest=digest(closing))
    return source, closing, provenance


def verify_owner_anchor(source, provenance):
    """Verify the immutable onboarding anchor; live owner generations may advance."""
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    anchor = MdmDailyInputCapture.objects.select_related('run').filter(
        source=source, run_id=provenance.get('run_id'), status='CONSUMED').first()
    if (provenance.get('schema') != DAILY_OWNER_SCHEMA
            or provenance.get('source_digest') != source.digest
            or provenance.get('artifact_sha256') != source.receipt.get('artifact_sha256')
            or provenance.get('dll_sha256') != source.dll_digest
            or anchor is None or anchor.run.kind != 'DAILY_CHAIN'
            or anchor.run.status != 'SUCCEEDED'
            or anchor.run.output_digest != provenance.get('output_digest')
            or anchor.revision_digest != provenance.get('capture_digest')):
        raise ValueError('Family accepted closing anchor differs')


def current_capture(source, run):
    """Require one terminal consumed node; dates and UUIDs do not order commits."""
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    if run is None or run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED':
        raise ValueError('Combined MDM requires its own successful predecessor/publication')
    consumed = MdmDailyInputCapture.objects.filter(source=source, status='CONSUMED')
    capture = consumed.filter(run=run).first()
    predecessors = consumed.filter(run__predecessor_id__isnull=False).values('run__predecessor_id')
    terminals = list(consumed.exclude(run_id__in=predecessors).values_list('run_id', flat=True)[:2])
    if capture is None or terminals != [run.pk]:
        raise ValueError('Combined MDM requires one unambiguous own terminal consumed generation')
    return capture


@transaction.atomic
def bind(source, run, *, require_all_families=False):
    """Seal an explicitly installed roster after accepted same-source closing."""
    from mta.mdm.supplier_revisions import lock_transaction
    from mta.presentation.context import selected_run
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    lock_transaction(source.pk)
    source = MdmSource.objects.select_for_update().get(pk=source.pk)
    require_unsealed(source)
    families = owner_identity(source)
    if require_all_families and set(families) != {str(i) for i in range(1, 14)}:
        raise ValueError('Complete MDM integration requires all thirteen masters')
    if selected_run().pk != run.pk:
        raise ValueError('Combined MDM requires the explicit accepted selected publication')
    anchor = current_capture(source, run)
    if MdmDailyInputCapture.objects.filter(source=source, status='CAPTURED',
                                           retries__isnull=True).exists():
        raise ValueError('Combined MDM requires its latest own closing and no pending capture')
    from mta.runtime.validation_storage import read_input
    snapshot = read_input(anchor.run, components=('mdm_input',)).get('mdm_input')
    if (not snapshot or snapshot.get('source_id') != source.pk
            or snapshot.get('source_digest') != source.digest
            or snapshot.get('revision_digest') != anchor.revision_digest):
        raise ValueError('Combined MDM accepted capture has a different original source identity')
    from importlib import import_module
    for mid, family in ((6, 'stop_pipo'), (7, 'phase_controls'), (10, 'season'), (13, 'force')):
        if str(mid) in families:
            owner = import_module('mta.mdm.' + family + '_source').require_installed(source)
            if owner.last_run_id != run.pk:
                raise ValueError('Combined MDM families require the same committed predecessor')
    p = dict(schema=SCHEMA, source_digest=source.digest, families=families,
        adapter_sha256=adapter_digest(), configuration=configuration_digest({int(mid) for mid in families}),
        run_id=str(anchor.run_id), output_digest=anchor.run.output_digest,
        capture_digest=anchor.revision_digest)
    if require_all_families:
        from mta.mdm.supplier_source import require_installed
        supplier = require_installed(source, 4)
        if (supplier.provenance.get('schema') != DAILY_OWNER_SCHEMA
                or supplier.provenance.get('run_id') != str(run.pk)
                or supplier.provenance.get('capture_digest') != anchor.revision_digest):
            raise ValueError('Complete MDM supplier owner requires the same accepted closing')
        p['required_families'] = list(range(1, 14))
    seal = MdmSourceIntegration.objects.create(source=source, digest=digest(p), receipt=p)
    installed_binding(source)
    return seal


@transaction.atomic
def bind_complete(source, run):
    """Onboard all optional families from one closing and seal them atomically."""
    from importlib import import_module
    for family in ('supplier', 'stop_pipo', 'phase_controls', 'force', 'season'):
        import_module('mta.mdm.' + family + '_source').bind(source, run)
    return bind(source, run, require_all_families=True)


def capture_identity(source):
    seal = installed_binding(source)
    return None if seal is None else dict(schema=SCHEMA, digest=seal.digest,
                                          families=seal.receipt['families'])


def verify_capture(source, snapshot):
    expected = capture_identity(source)
    _verify_capture_identity(source, snapshot, expected)


def _verify_capture_identity(source, snapshot, expected):
    if snapshot.get('integration') != expected:
        raise ValueError('Frozen MDM integration binding differs')
    if expected is not None:
        if snapshot.get('source_id') != source.pk or snapshot.get('source_digest') != source.digest:
            raise ValueError('Frozen MDM original source identity differs')
        ids = {int(mid) for mid in expected['families']}
        for key, group in CAPTURES.items():
            if (key in snapshot) != (group <= ids):
                raise ValueError('Frozen MDM family capture roster differs')


def require_current_run(source, run, seal, *, read_only=False):
    """Require this source's own latest consumed generation, never a fallback."""
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    if source.receipt.get('schema') == SOURCE_SCHEMA:
        capture = current_capture(source, run)
        from mta.runtime.validation_storage import read_input
        snapshot = read_input(run, components=('mdm_input',)).get('mdm_input')
        if snapshot is None or snapshot.get('revision_digest') != capture.revision_digest:
            raise ValueError('Native MDM predecessor capture differs')
        if read_only:
            _verify_capture_identity(source, snapshot, dict(schema=SCHEMA,
                digest=seal.digest, families=seal.receipt['families']))
        else:
            verify_capture(source, snapshot)
        for module in ('force', 'season', 'stop_pipo', 'phase_controls'):
            owner = __import__('mta.mdm.'+module+'_source', fromlist=['require_installed']).require_installed(source)
            if owner.last_run_id != run.pk:
                raise ValueError('Native MDM owner predecessor differs')
        return
    capture = current_capture(source, run)
    if seal.receipt.get('schema') == 'fresh-production-mdm-integration-v1' or str(run.pk) != seal.receipt['run_id']:
        from mta.runtime.validation_storage import read_input
        snapshot = read_input(run, components=('mdm_input',)).get('mdm_input')
        if snapshot is None or snapshot.get('revision_digest') != capture.revision_digest:
            raise ValueError('Combined MDM predecessor capture differs')
        verify_capture(source, snapshot)


def verify_predecessor(source, run, *, retry_capture=None):
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    seal = installed_binding(source)
    if seal is not None:
        from mta.mdm.initialization_contract import SOURCE_SCHEMA
        if source.receipt.get('schema') == SOURCE_SCHEMA and run is None:
            if MdmDailyInputCapture.objects.filter(source=source, status='CONSUMED').exists():
                raise ValueError('Native MDM opening is no longer the current predecessor')
            captures = MdmDailyInputCapture.objects.filter(source=source)
            if captures.exists() and (retry_capture is None or not captures.filter(
                    pk=retry_capture.pk, status='CAPTURED', run__status='FAILED',
                    run__predecessor__isnull=True).exists()):
                raise ValueError('Native root requires its explicit failed capture retry')
            for module in ('force', 'season', 'stop_pipo', 'phase_controls'):
                owner = __import__('mta.mdm.'+module+'_source', fromlist=['require_installed']).require_installed(source)
                if owner.last_run_id is not None:
                    raise ValueError('Native MDM opening owner already advanced')
            return
        require_current_run(source, run, seal)


def require_read_binding(source, *, read_only=False):
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    if read_only and source.receipt.get('schema') == SOURCE_SCHEMA:
        from mta.mdm.production_families import require_binding
        from mta.presentation.context import selected_run
        seal = require_binding(source, read_only=True)
        from mta.presentation.installation_metadata import publication_configured
        if not publication_configured():
            from mta.runtime.models import CalculationRun
            from mta.runtime.mdm_daily_models import MdmDailyInputCapture
            if (CalculationRun.objects.exists()
                    or MdmDailyInputCapture.objects.filter(source=source).exists()):
                raise ValueError('Initialized master read requires an untouched native opening')
            return seal
        require_current_run(source, selected_run(), seal, read_only=True)
        return seal
    seal = installed_binding(source)
    if seal is None:
        return
    if source.receipt.get('schema') == SOURCE_SCHEMA:
        return seal
    from mta.presentation.context import selected_run
    run = selected_run()
    require_current_run(source, run, seal)
    from importlib import import_module
    for mid, family in ((6, 'stop_pipo'), (7, 'phase_controls'), (10, 'season'), (13, 'force')):
        if str(mid) in seal.receipt['families']:
            owner = import_module('mta.mdm.' + family + '_source').require_installed(source)
            if owner.last_run_id != run.pk:
                raise ValueError('Combined MDM reader generation differs from selected publication')


def replace_working_inputs(snapshot, prior, day, predecessor):
    """Check both whole-opening anchors before changing either working table."""
    root_digest = digest(prior) if predecessor is None else None
    from mta.mdm.force_capture import prepare_working_input as prepare_force
    from mta.mdm.season_capture import prepare_working_input as prepare_season
    changes = (prepare_force(snapshot, prior, day, predecessor),
               prepare_season(snapshot, prior, day, predecessor))
    for apply in changes:
        if apply is not None:
            apply()
    from mta.mdm.stop_pipo_capture import replace_working_input as replace_stop
    from mta.mdm.phase_controls_capture import replace_working_input as replace_phase
    replace_stop(snapshot, prior, day, predecessor, opening_digest=root_digest)
    replace_phase(snapshot, prior, day, predecessor, opening_digest=root_digest)
