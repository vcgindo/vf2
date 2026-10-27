"""Logical PostBPR report sources over immutable accepted physical images.

These sources do not adopt/enable a report definition. Publication must separately
bind the selected definition to captured configuration and recheck its owner.
No current master rows are read and no accepted state is changed.
"""
from copy import deepcopy

from mta.serialization import digest, storage
from mta.row_sequences import RecordRows
from mta.application import runtime_demand_reports as demand
from mta.application.runtime_report_projection import describe
from mta.domain.complete_daily_scalars import ascii_equal

IMPORT_DATA_SHA256 = 'c248baeedda13d74a71a499c8b59b7ec46f05f11db00938de59a746bce94ce93'


def _hook(bound):
    from mta.runtime.input_reader import read_input
    from mta.application.runtime_report_hooks import configuration
    raw = read_input(bound.phase.run, components=('profile', 'scope_request'))
    request = raw.get('scope_request')
    if (type(request) is not dict or type(raw.get('profile')) is not dict
            or digest(raw.get('profile')) != bound.identity['profile_digest']
            or digest(request) != bound.identity['captured_request_digest']):
        raise ValueError('PostBPR hook captured configuration changed')
    site = raw['profile'].get('delivery', {}).get('site_code')
    if 'report_hooks' in request:
        # New generic intake must explicitly capture this declaration. Existing
        # request factories do not enable it by accepting arbitrary new fields.
        value = configuration(request['report_hooks'])
        if value['site_code'] != site:
            raise ValueError('PostBPR hook site differs from captured profile')
        kind = 'captured-production-declaration'
    else:
        # Historical TEST authority is checked by its original validator and
        # database boundary. It is never promoted to production configuration.
        from mta.runtime.production_upto_dbm import SCHEMA, disposition
        from mta.runtime.scope_runtime_reports import require_test_database
        if request.get('schema') != SCHEMA or request.get('scope') != 'UptoDBM':
            raise ValueError('Captured PostBPR hook disposition is absent')
        require_test_database()
        value = disposition(request.get('dispositions'))
        if value['site_code'] != site:
            raise ValueError('PostBPR test hook site differs from captured profile')
        kind = 'captured-owned-test-disposition'
    reference = dict(kind=kind, placement='PostBPR', mode=value.get('mode', 'declared-no-op'),
        site_code=site, configuration_digest=digest(value), owner=deepcopy(bound.identity))
    reference['digest'] = digest(reference)
    return reference


def _image(bound, node, path, table, fields):
    return bound.image(node, logical_image='phase/BPR/'+path,
                       physical_table=table, fields=fields)


def _copies(bound):
    """Reconstruct the same four typed copies; compare accepted full identities.

    Use the existing owner scalar conversion incrementally rather than retaining
    four additional full lists solely to calculate their partition digests.
    """
    from mta.runtime import mdm_models as models
    from mta.mdm.master_owners import business_fields, typed_field
    result, references, identities = {}, {}, []

    def projected(rows, model, fields):
        return RecordRows(len(rows), lambda: (
            {field.name: typed_field(model, field, row[field.name]) for field in fields}
            for row in rows))

    for family, table, model in (
            (1, 'SkuAttributeData', models.MdmSkuAttributes),
            (1, 'SKUDescriptionTbl', models.MdmSkuDescription),
            (2, 'LocationAttributeData', models.MdmLocationAttributes),
            (2, 'SiteDescriptionTbl', models.MdmLocationDescription)):
        fields = business_fields(model)
        names = tuple(field.name for field in fields)
        rows, physical = _image(bound, ('state', 'importer', table), 'importer/'+table,
                                'Importer/'+table, names)
        rows = projected(rows, model, fields)
        identity = dict(family=family, model=model.__name__, owner='BPR',
                        fields=list(names), rows=len(rows), digest=digest(storage(rows)))
        identities.append(identity)
        result['BPR/'+table] = rows
        references['BPR/'+table] = dict(kind='verified-accepted-bpr-copy',
            import_sql_sha256=IMPORT_DATA_SHA256, physical=physical, partition=identity)
    if identities != bound.phase.metadata.get('partitions'):
        raise ValueError('Accepted BPR copy partition identity differs')
    return result, references


def bind_post_bpr(bound, *, definition):
    """Return exact query source bags and provenance, never file readiness."""
    from mta.runtime.runtime_report_phase_sources import PhaseSources
    if (type(bound) is not PhaseSources or bound.phase.phase != 'BPR'
            or type(definition) is not dict
            or not ascii_equal(definition.get('Placement'), 'PostBPR')):
        raise ValueError('Exact accepted PostBPR report cut required')
    spec = describe(definition)
    if spec['captured_source_id'] not in (7, 10):
        raise ValueError('Runtime report has no PostBPR source adapter')
    hook = _hook(bound)
    sources, references = {}, {}

    def direct(logical, node, path, table, fields):
        sources[logical], physical = _image(bound, node, path, table, fields)
        references[logical] = dict(kind='accepted-bpr-producer', physical=physical)

    if spec['captured_source_id'] == 7:
        direct('BPR/SpikeOrderData', ('state', 'order_state', 'SpikeOrderData'),
               'orders/SpikeOrderData', 'BPR/SpikeOrderData', demand.SPIKE_FIELDS)
    else:
        direct('BPR/vf_RationedReqReport', ('state', 'late', 'vf_RationedReqReport'), 'late/vf_RationedReqReport',
               'BPR/vf_RationedReqReport', demand.RATIONED_FIELDS)
        direct('BPR/SupplierDispatchReq', ('state', 'complete', 'SupplierDispatchReq'),
               'complete/SupplierDispatchReq', 'complete/BPR/SupplierDispatchReq',
               ('SKUCode', 'WHCode', 'SupplierCode', 'OriginalReq', 'DispatchReq', *demand.SUPPLIER_BANDS))
        copies, copy_refs = _copies(bound)
        for logical in ('BPR/SiteDescriptionTbl', 'BPR/SkuAttributeData', 'BPR/LocationAttributeData'):
            sources[logical], references[logical] = copies[logical], copy_refs[logical]
        # Canonical ImportData SELECT * is an identity copy. There is no accepted
        # MDM BPR pair partition; retain that distinction in the witness.
        from mta.runtime.phase_state import REGISTRY
        table = 'Importer/SkuLocAttributeData'
        fields = tuple(name for name, _kind in REGISTRY[table])
        rows, physical = _image(bound, ('state', 'importer', 'SkuLocAttributeData'),
                                'importer/SkuLocAttributeData', table, fields)
        sources['BPR/SkuLocAttributeData'] = rows
        references['BPR/SkuLocAttributeData'] = dict(kind='reconstructed-canonical-copy',
            import_sql_sha256=IMPORT_DATA_SHA256, physical=physical,
            fields=list(fields), rows=len(rows), digest=digest(storage(rows)),
            persisted_bpr_partition=False)
    if set(sources) != set(spec['sources'].values()):
        raise ValueError('PostBPR logical report source roster differs')
    provenance = dict(schema='fresh-runtime-report-bpr-sources-v1',
        owner=deepcopy(bound.identity), query_sha256=spec['query_sha256'],
        definition_digest=digest(definition), hook=hook, sources=references)
    provenance['digest'] = digest(provenance)
    return sources, provenance
