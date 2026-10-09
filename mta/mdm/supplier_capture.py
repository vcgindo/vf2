"""Supplier extension of the existing frozen execute_day revision.

The daily input manifest stores these bags in typed image tables. Queue and
raw-owner changes commit only with the existing atomic run publication.
"""
from copy import deepcopy
from datetime import datetime

from mta.mdm.supplier_input import compose_supplier_inputs, archive_populations
from mta.mdm.supplier_source import MODELS, require_installed
from mta.mdm.task_reads import sql_key
from mta.runtime.mdm_supplier_models import (MdmSupplierConfiguration,
    MdmSobApproved, MdmMoqWithDestinationApproved, MdmMoqWithoutDestinationApproved,
    MdmSobArchive, MdmMoqWithDestinationArchive, MdmMoqWithoutDestinationArchive,
    MdmSobHistory, MdmMoqHistory)
from mta.serialization import digest, storage
from mta.mdm.supplier_revisions import task_revisions

QUEUES = {'NMSSOB': MdmSobApproved, 'NMSMOQWithDestination': MdmMoqWithDestinationApproved,
          'NMSMOQWithoutDestination': MdmMoqWithoutDestinationApproved}
ARCHIVES = {'NMSSOB': MdmSobArchive, 'NMSMOQWithDestination': MdmMoqWithDestinationArchive,
            'NMSMOQWithoutDestination': MdmMoqWithoutDestinationArchive}


def columns(model):
    return [f.name for f in model._meta.fields if f.name not in ('id', 'source', 'ordinal', 'revision')]


def capture(source):
    if not MdmSupplierConfiguration.objects.filter(source=source).exists():
        return None
    config = require_installed(source, 4)
    require_installed(source, 5)
    result = dict(moq_format=config.moq_format, source_digest=config.receipt_digest,
        raw={name: list(model.objects.filter(source=source).order_by('ordinal').values(*columns(model)))
             for name, model in MODELS.items()},
        queues={name: list(model.objects.filter(source=source).order_by('id').values('id', 'revision', *columns(model)))
                for name, model in QUEUES.items()}, task_revisions=task_revisions(source))
    from mta.runtime.mdm_models import MdmTask, MdmSubTask
    pending = []
    for mid, family, model in ((4, 'sob', MdmSobHistory), (5, 'moq', MdmMoqHistory)):
        task_ids = MdmTask.objects.filter(source=source, MasterId=str(mid), Actiontype=1,
            TaskID__in=MdmSubTask.objects.filter(source=source, TaskStatus__in=('1', '8')).values('TaskID'))
        for row in model.objects.filter(source=source, TaskId__in=task_ids.values('TaskID')).order_by('id'):
            values = {name: storage(getattr(row, name)) for name in columns(model)}
            pending.append(dict(family=family, history_pk=row.pk, task_id=row.TaskId,
                                row_digest=digest(values)))
    result['pending'] = pending
    result['digest'] = digest(result)
    return storage(result)


def location_master(location_rows):
    """NMSImportData LocationMaster FULL JOIN plus approved description UPDATE."""
    descriptions = location_rows['descriptions']; approved = location_rows['approved']
    equal = lambda a, b: a is not None and b is not None and sql_key(a) == sql_key(b)
    rows = []
    for left in descriptions:
        matches = [r for r in approved if equal(left['WHCode'], r['WHCode'])] or [None]
        for right in matches:
            rows.append(dict(WHCode=left['WHCode'], WHDescription=left['WHDescription']
                if left['WHDescription'] is not None else right['WHDescription'] if right else None))
    rows.extend(dict(WHCode=r['WHCode'], WHDescription=r['WHDescription']) for r in approved
                if not any(equal(r['WHCode'], left['WHCode']) for left in descriptions))
    for row in rows:
        values = [r['WHDescription'] for r in approved if r['Approved'] and r['ActionType'] == 1
                  and equal(row['WHCode'], r['WHCode'])]
        if values:
            if any(value != values[0] for value in values[1:]):
                raise ValueError('SOURCE_ORDER_AMBIGUITY: supplier LocationMaster UPDATE')
            row['WHDescription'] = values[0]
    return rows


def feeds(snapshot):
    supplier = snapshot['supplier']
    if digest({k: v for k, v in supplier.items() if k != 'digest'}) != supplier['digest']:
        raise ValueError('Supplier capture identity drift')
    queues = {name: [{k: v for k, v in row.items() if k not in ('id', 'revision')} for row in rows]
              for name, rows in supplier['queues'].items()}
    return compose_supplier_inputs(supplier['raw'], queues,
        moq_format=supplier['moq_format'], locations=location_master(snapshot['rows']['location']))


def require_format(snapshot, importer_settings):
    """Do not let the API's selected queue format replace the engine setting."""
    if not snapshot['nms_active'] or 'supplier' not in snapshot:
        return
    values = [row['Value'] for row in importer_settings
              if sql_key(row.get('Parameter')) == 'nmsmoqinputdataformat']
    expected = snapshot['supplier']['moq_format']
    if not values or any(value != expected for value in values):
        raise ValueError('Captured supplier format differs from explicit importer setting')


def finalize(run, snapshot, output):
    """Called under finish_run's transaction; never recalculate a day here."""
    if not snapshot['nms_active'] or 'supplier' not in snapshot:
        return
    supplier = snapshot['supplier']
    from mta.runtime.mdm_models import MdmSource
    source = MdmSource.objects.select_for_update().get(pk=snapshot['source_id'])
    current = capture(source)
    if (current['source_digest'] != supplier['source_digest']
            or current['moq_format'] != supplier['moq_format'] or current['raw'] != supplier['raw']):
        raise ValueError('Captured supplier raw/configuration changed before publication')
    if output is None:
        raise ValueError('Supplier publication requires actual producer output')
    final = [stage['tables'] for stage in output['SupplierStages'] if stage['stage'] == 'ResetFlags.sql']
    if len(final) != 1:
        raise ValueError('Exact terminal supplier producer required')
    selected = archive_populations(supplier['queues'], moq_format=supplier['moq_format'])
    for name, model in QUEUES.items():
        for ordinal, frozen in enumerate(supplier['queues'][name], 1):
            row = model.objects.select_for_update().get(source=source, pk=frozen['id'])
            values = storage({n: getattr(row, n) for n in columns(model)})
            captured_values = {k: v for k, v in frozen.items() if k not in ('id', 'revision')}
            scalar = 'SOB' if name == 'NMSSOB' else 'MOQ'
            same_revision = row.revision == frozen['revision']
            if (row.revision < frozen['revision']
                    or any(value != captured_values[key] for key, value in values.items()
                           if same_revision or key != scalar)):
                raise ValueError('Captured supplier queue occurrence changed before publication')
            if name in selected:
                ARCHIVES[name].objects.create(source=source, run=run, source_pk=row.pk,
                    ordinal=ordinal, Input_Date=datetime.fromisoformat(snapshot['configuration']['run_timestamp']), **captured_values)
            if same_revision and frozen['Approved']:
                row.delete()
    for name, model in MODELS.items():
        model.objects.filter(source=source).delete()
        model.objects.bulk_create([model(source=source, ordinal=i, **row)
            for i, row in enumerate(final[0][name], 1)])


def finalize_pending(snapshot, output, *, deferred_tasks=()):
    """NMSTaskStatusUpdate pending-Add section, after approved transitions."""
    if 'supplier' not in snapshot:
        return
    supplier = snapshot['supplier']
    if not supplier['pending']:
        return
    if output is None:
        raise ValueError('Supplier pending history requires producer output')
    final = next(stage['tables'] for stage in output['SupplierStages'] if stage['stage'] == 'ResetFlags.sql')
    for item in supplier['pending']:
        if (4 if item['family'] == 'sob' else 5, item['task_id']) in deferred_tasks:
            continue
        sob = item['family'] == 'sob'
        model = MdmSobHistory if sob else MdmMoqHistory
        row = model.objects.select_for_update().get(source_id=snapshot['source_id'], pk=item['history_pk'])
        if digest({name: storage(getattr(row, name)) for name in columns(model)}) != item['row_digest']:
            raise ValueError('Captured supplier pending history changed before publication')
        names = ('SKUCode', 'WhCode', 'SupplierCode') if sob or supplier['moq_format'] == 'WithDestLoc' else ('SKUCode', 'SupplierCode')
        identity = tuple(sql_key(getattr(row, n)) for n in names)
        if None in identity:
            continue
        # The native WithoutDestLoc branch also reads Raw2, not Raw1.
        raw = final['SOBDataRaw' if sob else 'MOQDataRaw2']
        if any(identity == tuple(sql_key(r['WHCode' if n == 'WhCode' else n]) for n in names) for r in raw):
            row.Status = '4'; row.Comments = 'Already in Vectorflow'
            row.save(update_fields=['Status', 'Comments'])
