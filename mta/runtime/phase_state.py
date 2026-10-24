"""Typed live-out snapshots before BPR, after BPR and before BTR.

A sealed snapshot is calculation storage, not phase business acceptance, file
readiness, selection or a successful predecessor. The scoped transaction owner
must commit its mapped effects and acceptance separately before exposing it.
"""
import inspect

from django.db import connection, transaction
from mta.serialization import digest, canonical_parts
from mta.runtime import relational_state as typed
from mta.runtime.phase_state_schema import TABLES

SCHEMA = 'fresh-native-phase-state-v1'
REGISTRY = {**typed.STORAGE_TABLES, **TABLES}
# These are the unchanged captured opening/fact dependencies read by remaining
# calculation. Preparation's consumed requests and reset flags are not reread.
PRIOR_REFS = ('dbm', 'btr', 'bpr', 'orders', 'consumer_context', 'publication_context')
DAY_REFS = ('business_date', 'raw_non_nms', 'raw_no_norm', 'order_raw', 'exclusions',
            'distributor_transactions', 'vendor_transactions', 'order_feed', 'order_feed_status')
OPTIONAL_DAY_REFS = ('requirement_stock', 'production_report_policy')


def recipe_digest():
    from mta.temporal import chain, day_phases
    return digest(dict(codec=inspect.getsource(inspect.getmodule(recipe_digest)),
        chain=inspect.getsource(chain), phases=inspect.getsource(day_phases),
        registry=REGISTRY))


def _references(context):
    return dict(prior={name: digest(context.prior[name]) for name in PRIOR_REFS},
        day={name: digest(context.day[name]) for name in DAY_REFS},
        optional_day={name: (digest(context.day[name]) if name in context.day else None)
                      for name in OPTIONAL_DAY_REFS},
        profile=digest(context.profile), master_snapshot=digest(context.master_snapshot))


def _table(binding):
    if binding in typed.COMPLETE_BINDINGS:return typed.COMPLETE_BINDINGS[binding]
    if binding in typed.PHASE_BINDINGS:return typed.PHASE_BINDINGS[binding]
    if binding in typed.BTR_BINDINGS:return typed.BTR_BINDINGS[binding]
    if binding not in typed.CATALOG['bindings']:
        raise ValueError('Undeclared continuation population: '+binding)
    return '/'.join(typed.CATALOG['bindings'][binding])


def _write_rows(run, path, table, rows):
    """Same scalar conversion/ordinal transport as daily storage, own namespace."""
    columns = {name.casefold(): (name, kind) for name, kind in REGISTRY[table]}
    meta, fields, native = typed.describe_rows(rows, columns, path)
    meta['table'] = table
    if rows:
        query = ('INSERT INTO '+typed.table_sql(table)+
            ' (vf_run_id,vf_image,vf_ordinal,'+
            ','.join(typed.quote(name) for name, _ in native)+') VALUES ('+
            ','.join(['%s']*(len(native)+3))+')')
        typed.bulk(query, ((run.pk, path, ordinal, *[
            typed.db_value(row[field], kind)
            for field, (_, kind) in zip(fields, native)])
            for ordinal, row in enumerate(rows)))
    if digest(typed.load_image(run, meta, table_registry=REGISTRY)) != digest(rows):
        raise ValueError('Continuation typed readback differs: '+path)
    return meta


def encode(phase, sources, *, row_writer, export_writer, parent_manifest=None):
    """Build only shape/reference metadata; every operational cell is typed."""
    from mta.temporal.day_phases import PreparedDay, BprDay, DbmDay
    from mta.application.stage_calculation_sources import CalculationSources
    if type(phase) not in (PreparedDay, BprDay, DbmDay) or not phase.context.native_daily:
        raise ValueError('Native prepared/BPR/pre-BTR DBM phase required')
    name = {PreparedDay: 'PRE_BPR', BprDay: 'BPR', DbmDay: 'DBM'}[type(phase)]
    if (name == 'PRE_BPR' and sources is not None or
            name != 'PRE_BPR' and not isinstance(sources, CalculationSources)):
        raise ValueError('Calculation sources must match their producing phase')
    images = {}
    parent_images = (parent_manifest or {}).get('images', {})

    def rows(path, values, *, binding=None, table=None):
        table = table or _table(binding)
        path = 'phase/'+name+'/'+path
        columns = {n.casefold(): (n, kind) for n, kind in REGISTRY[table]}
        meta, _, _ = typed.describe_rows(values, columns, path)
        meta['table'] = table
        inherited = (parent_images.get(path.replace('phase/'+name+'/',
            'phase/'+parent_manifest['phase']+'/', 1)) if parent_manifest else None)
        if inherited is not None and all(meta[k] == inherited[k]
                for k in ('table', 'count', 'digest', 'fields')):
            images[path] = inherited
        else:
            images[path] = row_writer(path, table, values)
        return {'image': path}

    def tables(values, prefix, binding_prefix):
        if values is None:return None
        result = {}
        for key, values in values.items():
            if key == 'IntermediateTables':
                entries = values.items() if isinstance(values, dict) else (
                    (row['table'], row['rows']) for row in values)
                result[key] = {'scratch_kind': 'dict' if isinstance(values, dict) else 'list',
                    'items': [[n, rows(prefix+'/'+key+'/'+n, bag, binding='scratch/'+n)]
                              for n, bag in entries]}
            else:
                result[key] = rows(prefix+'/'+key, values, binding=binding_prefix+'/'+key,
                    table=({'MasterDataRawNonNMS': 'Intermediate/TempMasterDataRawNonNMS',
                            'NoNormMasterRaw': 'Intermediate/NoNormMasterRaw'}.get(key, 'Importer/'+key)
                           if binding_prefix == 'closing/importer' else None))
        return result

    state = dict(
        importer=tables(phase.importer, 'importer', 'closing/importer'),
        control_final=tables(phase.control_final, 'controls', 'closing/controls'),
        control_aux=tables(phase.control_aux, 'aux', 'closing/control_aux'),
        diagnostics=tables(phase.diagnostics, 'diagnostics', 'reports/controls'),
        nms=(None if phase.nms is None else {
            key: rows('nms/'+key, values, table='Importer/'+key)
            for key, values in phase.nms.items()}),
        supplier_sob=rows('supplier/sob', phase.supplier_sob, table='BPR/SOBData'),
        supplier_moq=rows('supplier/moq', phase.supplier_moq, table='BPR/MOQData'),
        complete=tables(phase.complete, 'complete', 'closing/complete'),
        master_raw=rows('master_raw', phase.context.master['tables']['MasterDataRaw'],
                        table='Importer/MasterDataRaw'))
    if name == 'PRE_BPR':
        from mta.application.r1_daily_entry import generated_bpr_daily_state
        consumption = (generated_bpr_daily_state(dict(
            raw_master_entry={'business_date': phase.context.today},
            raw_daily_entry=phase.daily_input), phase.daily)
            if phase.daily_consumption is None else phase.daily_consumption)
        state.update(daily_consumption=rows('daily_consumption', consumption, table='BPR/DailyConsumption'),
            old_sourcing=rows('old_sourcing', phase.old_sourcing, table='phase/Sourcing'),
            new_sourcing=rows('new_sourcing', phase.new_sourcing, table='phase/Sourcing'),
            supplier_final={key: rows('supplier_raw/'+key, phase.supplier_final[key], table=table)
                for key, table in (('SOBDataRaw', 'Intermediate/TempSOBDataRaw'),
                    ('MOQDataRaw1', 'Intermediate/TempMOQDataRaw1'),
                    ('MOQDataRaw2', 'Intermediate/TempMOQDataRaw2'))})
    else:
        state.update(bpr_master=rows('bpr_master', phase.bpr_master, binding='closing/bpr/BPRMaster'),
            order_state=tables({key: phase.order_state[key] for key in phase.context.prior['orders']},
                               'orders', 'closing/orders'),
            report=rows('report', phase.report, binding='reports/bpr/vf_RationedReqReport'),
            late={key: rows('late/'+key, values, table={
                'BPR_Table': 'BPR/BPR_Table', 'BPRDailyConsumption': 'BPR/DailyConsumption',
                'BPRLastBatchRunTbl': 'DBM/LastBatchRunTbl',
                'vf_RationedReqReport': 'BPR/vf_RationedReqReport'}[key])
                for key, values in phase.late.items()},
            pick_state=(None if phase.pick_state is None else tables(
                {key: phase.pick_state[key] for key in ('LogisticPickList', 'PickListDataForTruckFormation')},
                'pick', 'closing/complete')))
    from mta.runtime.operational_input_source import STORAGE_BINDINGS
    from mta.runtime.operational_force_source import BINDINGS
    for key, values, bindings in (
        ('operational_input_tables', getattr(phase, 'operational_input_tables', None), STORAGE_BINDINGS),
        ('force_alert_capture', phase.force_alert_capture, BINDINGS)):
        state[key] = None if values is None else {
            n: rows(key+'/'+n, bag, table=bindings[n]) for n, bag in values.items()}
    consumers = None if name == 'PRE_BPR' else dict(
        pick_bands=rows('sources/pick', sources.pick_bands, table='phase/PickBand'),
        routes=rows('sources/routes', sources.routes, table='Intermediate/InterNodeOrders'),
        operational=(None if sources.operational is None else {
            key: rows('sources/operational/'+key, values, table={
                'requirement_bands': 'Intermediate/RequirementInColorBand',
                'advance_stock_allocations': 'phase/AdvanceStock'}[key])
            for key, values in sources.operational.items()}),
        production_reports=(None if sources.production_reports is None else {
            key: rows('sources/production/'+key, values, table='production/'+key)
            for key, values in sources.production_reports.items()}))
    if name in ('PRE_BPR', 'BPR'):
        state['daily_final'] = {key: rows('daily/'+key, phase.daily_final[key],
                table='Intermediate/TempDailyDataRaw') for key in
                (('DailyDataRaw', 'DailyDataProcessed') if name == 'PRE_BPR' else ('DailyDataRaw',))}
        state['standard_attributes'] = (None if phase.standard_attributes is None else
            rows('standards', phase.standard_attributes, table='Importer/SKULocStandardAttributes'))
    else:
        state['final_dbm'] = tables(phase.final_dbm, 'dbm', 'closing/dbm')
        reports = []
        for report in phase.reports or []:
            stage = report['stage']
            binding_stage = 'norm0-export' if stage in ('norm0-60-export', 'norm0-90-export') else stage
            item = dict(stage=stage, tables={})
            for key, values in report['tables'].items():
                path = 'reports/'+stage+'/'+key
                item['tables'][key] = ({'export': export_writer('phase/DBM/'+path, values)}
                    if key in ('ReportHeader', 'ReportRows') else
                    rows(path, values, binding='reports/'+binding_stage+'/'+key))
            if 'deferred' in report:
                item.update(deferred=report['deferred'], sources=tables(report['sources'],
                    'report-facts/'+stage, 'closing/dbm'))
            reports.append(item)
        state['reports'] = reports
    context = phase.context
    metadata = dict(opening_date=context.opening_date, identity=context.identity,
        completed_boundaries=list(phase.completed_boundaries),
        report_exceptions=context.report_exceptions, master_outcome=context.master['outcome'],
        master_reused=context.master_reused, master_work=context.master_work,
        pick_source_digests=(phase.pick_source_digests if getattr(phase, 'pick_sources', None) is None else
            {key: digest(values) for key, values in phase.pick_sources.items()}),
        calculation_digest=None if sources is None else sources.calculation_digest)
    result = dict(schema=SCHEMA, phase=name, references=_references(context),
                  metadata=metadata, state=state, consumers=consumers, images=images)
    if sum(len(part) for part in canonical_parts(result)) > 1024*1024:
        raise ValueError('Continuation shape metadata exceeds bounded manifest')
    return result


def decode(manifest, *, prior, day, profile, master_snapshot, row_reader, export_reader,
           execute_calculation=None):
    """Rehydrate only live-out state, using the same frozen dependency owners."""
    from mta.application.stage_calculation_sources import CalculationSources
    from mta.application.daily_finalization import configuration
    from mta.temporal.day_phases import DayContext, PreparedDay, BprDay, DbmDay
    from types import SimpleNamespace
    if manifest.get('schema') != SCHEMA or manifest.get('phase') not in ('PRE_BPR', 'BPR', 'DBM'):
        raise ValueError('Continuation schema/phase differs')
    refs = SimpleNamespace(prior=prior, day=day, profile=profile, master_snapshot=master_snapshot)
    if _references(refs) != manifest['references']:
        raise ValueError('Continuation captured dependency revision differs')

    def unpack(node):
        if isinstance(node, list):return [unpack(value) for value in node]
        if not isinstance(node, dict):return node
        if set(node) == {'image'}:return row_reader(manifest['images'][node['image']])
        if set(node) == {'export'}:return export_reader(node['export'])
        if 'scratch_kind' in node:
            values = [(name, unpack(value)) for name, value in node['items']]
            return dict(values) if node['scratch_kind'] == 'dict' else [
                {'table': name, 'rows': value} for name, value in values]
        return {key: unpack(value) for key, value in node.items()}

    state = unpack(manifest['state'])
    metadata = manifest['metadata']
    sources = (None if manifest['consumers'] is None else
               CalculationSources(metadata['calculation_digest'], **unpack(manifest['consumers'])))
    today = day['business_date']
    context = DayContext(prior=prior, day=day, opening_date=metadata['opening_date'],
        profile=profile, identity=metadata['identity'], execute_calculation=execute_calculation,
        report_exceptions=metadata['report_exceptions'], native_daily=True,
        master_snapshot=master_snapshot, today=today, now=today+'T00:00:00',
        finalization=configuration(profile), completion=None,
        master=dict(outcome=metadata['master_outcome'], tables={'MasterDataRaw': state.pop('master_raw')}),
        master_reused=metadata['master_reused'], master_work=metadata['master_work'])
    common = dict(context=context, delivery=profile.get('delivery'),
        completed_boundaries=list(metadata['completed_boundaries']),
        pick_source_digests=metadata['pick_source_digests'])
    if manifest['phase'] == 'PRE_BPR':
        if not callable(execute_calculation):
            raise ValueError('Prepared continuation requires the existing calculation callable')
        context.completion = state.pop('complete')
        context.prior = dict(prior, complete=context.completion)
        state.pop('operational_input_tables')
        phase = PreparedDay(**common, daily_input=None, daily=None, **state)
    else:
        phase_type = BprDay if manifest['phase'] == 'BPR' else DbmDay
        phase = phase_type(**common, calculated=None, pick_sources=None, **state)
    return phase, sources


def save(run, phase, sources, *, parent=None):
    """Seal typed storage atomically. Does not expose/accept a scope command."""
    from mta.runtime.models import CalculationRun, DailyPhaseSnapshot
    if transaction.get_autocommit():
        raise ValueError('Phase snapshot requires its owning transaction')
    with transaction.atomic():
        return _save(run, phase, sources, parent=parent)


def _save(run, phase, sources, *, parent):
    from mta.runtime.models import CalculationRun, DailyPhaseSnapshot
    owner = CalculationRun.objects.select_for_update().get(pk=run.pk)
    if (owner.status != 'RUNNING' or owner.kind != 'DAILY_CHAIN'
            or owner.output_digest or owner.checkpoints.exists()):
        raise ValueError('Phase snapshot requires its uncompleted daily owner')
    if parent is not None:
        parent = DailyPhaseSnapshot.objects.get(pk=parent.pk)
    if parent is not None and (parent.run_id != owner.pk or parent.phase not in ('PRE_BPR', 'BPR')
            or parent.state_digest != digest(parent.manifest)
            or parent.recipe_digest != recipe_digest()):
        raise ValueError('Continuation parent snapshot differs')
    from mta.temporal.day_phases import PreparedDay, BprDay, DbmDay
    if type(phase) is PreparedDay:
        valid_parent = parent is None
    elif type(phase) is BprDay:
        valid_parent = parent is None or parent.phase == 'PRE_BPR'
    elif type(phase) is DbmDay:
        valid_parent = parent is not None and parent.phase == 'BPR'
    else:
        valid_parent = False
    if (phase.context.identity != str(owner.pk)
            or phase.context.today != owner.business_date.isoformat()
            or not valid_parent):
        raise ValueError('Phase snapshot run/date/parent differs')
    manifest = encode(phase, sources,
        row_writer=lambda path, table, values: _write_rows(owner, path, table, values),
        export_writer=lambda path, values: typed.save_export(owner, path, values),
        parent_manifest=parent.manifest if parent else None)
    if parent is not None:
        if manifest['references'] != parent.manifest['references']:
            raise ValueError('Continuation parent dependency revision differs')
        if parent.phase == 'BPR' and consumer_identity(manifest) != consumer_identity(parent.manifest):
            raise ValueError('Continuation calculation consumers changed after BPR')
    return DailyPhaseSnapshot.objects.create(run=owner, phase=manifest['phase'], parent=parent,
        input_digest=owner.input_digest, recipe_digest=recipe_digest(),
        state_digest=digest(manifest), manifest=manifest)


def read(snapshot, **references):
    """Read the sealed snapshot; caller still owns action/effect/claim checks."""
    from mta.runtime.models import DailyPhaseSnapshot
    snapshot = DailyPhaseSnapshot.objects.select_related('run').get(pk=snapshot.pk)
    if (snapshot.input_digest != snapshot.run.input_digest
            or snapshot.recipe_digest != recipe_digest()
            or snapshot.state_digest != digest(snapshot.manifest)):
        raise ValueError('Continuation snapshot input/code/storage identity differs')
    return decode(snapshot.manifest, **references,
        row_reader=lambda item: typed.load_image(snapshot.run, item, table_registry=REGISTRY),
        export_reader=lambda item: typed.load_export(snapshot.run, item))


def consumer_identity(manifest):
    def bind(node):
        if node is None:return None
        if set(node) == {'image'}:
            item = manifest['images'][node['image']]
            return {key: item[key] for key in ('table', 'count', 'digest', 'fields')}
        return {key: bind(value) for key, value in node.items()}
    return dict(calculation_digest=manifest['metadata']['calculation_digest'],
                consumers=bind(manifest['consumers']))
