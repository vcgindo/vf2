"""Finite canonical batch files from one accepted BPR snapshot, for owned TEST.

This producer neither recalculates allocation nor continues allocation history.
InputData and Pick artifacts are outside its fixed file roster.
"""
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path

from mta.application import (operational_bor as bor, operational_exceptions as exceptions,
    operational_alert_files as alerts, operational_sqlcmd as sqlcmd,
    operational_report_files as files, operational_io)
from mta.application.r1_importer_master import MASTER_COLUMNS
from mta.domain.complete_daily_scalars import ascii_equal
from mta.domain import complete_daily_scalars
from mta.presentation.context import PublicationUnavailable
from mta.presentation import scoped_sources, native_report_colours
from mta.runtime import phase_state
from mta.runtime.relational_state import load_image
from mta.serialization import digest

SCHEMA = 'fresh-scoped-batch-files-v1'
TEST_DECLARATION = dict(purpose='owned-scoped-test', IsMTOEnvironment=0,
    excluded_optional_branches=['ModifiedRRR', 'DistSpecialOrder', 'DistTransaction'],
    allocation_history='unsupported-owned-test')


def recipe_digest():
    modules = (inspect.getmodule(recipe_digest), bor, exceptions, alerts, sqlcmd, files, operational_io,
               native_report_colours, complete_daily_scalars)
    return digest({module.__name__: inspect.getsource(module) for module in modules})


def _source(phase, node, table, fields, receipts):
    manifest = phase.snapshot.manifest
    logical = scoped_sources._image(manifest, node)
    if logical is None:
        raise PublicationUnavailable('bpr_batch_source_unavailable:' + '/'.join(node))
    item = scoped_sources._checked(manifest['images'].get(logical))
    if (not logical.startswith('phase/BPR/') or item['table'] != table
            or item['image'] not in (logical, logical.replace('phase/BPR/', 'phase/PRE_BPR/', 1))):
        raise PublicationUnavailable('bpr_batch_source_owner_differs:' + table)
    try:
        rows = load_image(phase.run, item, table_registry=phase_state.REGISTRY)
        available = {field for field, _, _ in item['fields']}
        if not available and item['count'] == 0:
            available = {field for field, _ in phase_state.REGISTRY[table]}
        if not set(fields) <= available:
            raise ValueError('Required typed fields absent')
        projected = []
        for row in rows:
            if not set(fields) <= set(row):
                raise ValueError('Required row fields absent')
            projected.append({field: row[field] for field in fields})
    except (ValueError, KeyError) as error:
        raise PublicationUnavailable('bpr_batch_source_rows_differ:' + table) from error
    receipts['/'.join(node)] = dict(logical_image=logical, physical_image=item['image'],
        table=table, count=item['count'], rows_digest=item['digest'], fields=deepcopy(item['fields']))
    return projected


def payload(phase_id, *, expected_digest, declaration):
    """Return canonical bytes and source metadata without writing any files."""
    from mta.runtime.scope_runtime_reports import require_test_database
    if declaration != TEST_DECLARATION or type(declaration.get('IsMTOEnvironment')) is not int:
        raise PublicationUnavailable('bpr_batch_explicit_test_declaration_required')
    require_test_database()
    phase = scoped_sources._accepted_phase(phase_id, expected_digest)
    if phase.phase != 'BPR':
        raise PublicationUnavailable('bpr_batch_accepted_bpr_required')
    sources = {}
    def read(node, table, fields):
        return _source(phase, node, table, fields, sources)
    sku = read(('state','importer','SKUDescriptionTbl'), 'Importer/SKUDescriptionTbl', bor.SKU_DESCRIPTION_FIELDS)
    site = read(('state','importer','SiteDescriptionTbl'), 'Importer/SiteDescriptionTbl', bor.SITE_DESCRIPTION_FIELDS)
    allocation = read(('consumers','production_reports','BORWithOrderAllocation'),
        'production/BORWithOrderAllocation', bor.BOR_COLUMNS)
    requirement = read(('consumers','production_reports','BOROARequirement'),
        'production/BOROARequirement', bor.REQ_REPORT_FIELDS)
    colours = native_report_colours.reference()
    report = bor.generate_bor_order_allocation(bor_rows=allocation, color_sequence=colours['rows'],
        sku_descriptions=sku, site_descriptions=site, requirement_rows=requirement,
        is_mto_environment=declaration['IsMTOEnvironment'], equal=ascii_equal)
    failed = read(('state','diagnostics','failed_force'), 'Projection/FailedForce',
                  ('SKUCode','WhCode','VectorFlowNorm','Reason'))
    # Same O3 source as operational_readers: processed importer MasterData,
    # before post-BPR DBM can change its Norms, and this phase's phase-out bag.
    master = read(('state','importer','MasterData'), 'Importer/MasterData', MASTER_COLUMNS)
    phased = read(('state','control_final','phase_out'), 'DBM/PhaseOutTbl', exceptions.PHASE_OUT_FIELDS)
    parent = exceptions.no_norm_at_parent_rows(master_data=master, phase_out=phased, equal=ascii_equal)
    bpr = read(('state','bpr_master'), 'BPR/BPRMaster', exceptions.BPR_MASTER_FIELDS)
    daily = read(('state','late','BPRDailyConsumption'), 'BPR/DailyConsumption', exceptions.DAILY_CONSUMPTION_FIELDS)
    today = phase.run.business_date.isoformat()
    exceptional = exceptions.bpr_exception_rows(bpr_master=bpr, daily_consumption=daily,
        business_date=today, equal=ascii_equal)
    result = dict(BOR_OrderAllocation=sqlcmd.bor_report_bytes(report),
        FailedForceNormChanges=alerts.failed_force_bytes(failed),
        NoNormParentReport=sqlcmd.no_norm_parent_bytes(parent),
        BPRExceptionReport=(sqlcmd.resultset_bytes(exceptions.bpr_exception_resultsets(exceptions=exceptional,
            sku_descriptions=sku, site_descriptions=site, equal=ascii_equal)) if exceptional else None))
    metadata = dict(schema=SCHEMA, run_id=str(phase.run_id), phase_id=str(phase.pk),
        phase_digest=phase.digest, snapshot_digest=phase.snapshot.state_digest,
        business_date=today, declaration=deepcopy(declaration), recipe_digest=recipe_digest(), sources=sources,
        colour_reference=deepcopy(colours), producer_sources=dict(bor=bor.SOURCES['report'],
            failed_force=alerts.SOURCES['force'], exceptions=exceptions.SOURCES,
            wrappers={key: files.SOURCES[key] for key in ('bor','force_norm','parent_norm','bpr_exceptions')}),
        counts=dict(BOR_OrderAllocation=len(report['data_resultset']), FailedForceNormChanges=len(failed),
            NoNormParentReport=len(parent), BPRExceptionReport=len(exceptional)),
        payloads={name: None if data is None else dict(size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                  for name, data in result.items()})
    metadata['digest'] = digest(metadata)
    return metadata, result


def prepare(phase_id, *, expected_digest, declaration, root, archive_writer=None):
    """Materialize only into a new exclusive directory; preserve it on failure."""
    destination = Path(root)
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        raise ValueError('New absolute exclusive batch-file directory required')
    metadata, data = payload(phase_id, expected_digest=expected_digest, declaration=declaration)
    if (data['NoNormParentReport'] or data['BPRExceptionReport'] is not None) and not callable(archive_writer):
        raise ValueError('Explicit canonical archive writer required for nonempty report branch')
    destination.mkdir(exist_ok=False)
    wrappers = dict(BOR_OrderAllocation=files.bor_report_files(root=destination,
        report_bytes=data['BOR_OrderAllocation']),
        FailedForceNormChanges=files.failed_force_report_files(root=destination,
            business_date=metadata['business_date'], report_bytes=data['FailedForceNormChanges']),
        NoNormParentReport=files.no_norm_parent_report_files(root=destination,
            report_bytes=data['NoNormParentReport'], archive_writer=archive_writer),
        BPRExceptionReport=files.bpr_exception_report_files(root=destination,
            exception_count=metadata['counts']['BPRExceptionReport'],
            report_bytes=data['BPRExceptionReport'], archive_writer=archive_writer))
    actual = [operational_io.inspect_file(destination, path.relative_to(destination).as_posix())
              for path in sorted(destination.rglob('*')) if path.is_file()]
    metadata = dict(metadata, payload_digest=metadata['digest'], wrappers=wrappers, files=actual)
    metadata.pop('digest')
    metadata['digest'] = digest(metadata)
    operational_io.write_file(destination, 'scoped-batch-files.json',
        (json.dumps(metadata, sort_keys=True, indent=2) + '\n').encode('utf-8'))
    paths = {item['relative_path']: str(destination / item['relative_path']) for item in actual}
    return metadata, dict(root=str(destination), manifest=str(destination / 'scoped-batch-files.json'), files=paths)
