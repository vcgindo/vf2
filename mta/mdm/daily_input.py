"""Frozen composed SKU/Location/SKU-location input for one daily run.

The composition order is the supported MasterDataRaw portion of the pinned
NMSImportData.sql.  Queue mutation is deliberately deferred to the atomic
successful publication boundary.
"""
from copy import deepcopy
from datetime import datetime, time, timedelta

from django.db import connection, transaction
from mta.application.r1_importer_master import RAW_COLUMNS
from mta.mdm.clock import database_now
from mta.mdm.location import ALIASES as LOCATION_ALIASES
from mta.mdm.sku import ALIASES as SKU_ALIASES
from mta.mdm.task_reads import sql_key
from mta.runtime.mdm_models import (MdmLocationApproved, MdmLocationAttributes,
    MdmLocationDescription, MdmLocationHistory, MdmSkuApproved,
    MdmSkuAttributes, MdmSkuDescription, MdmSkuHistory, MdmSource, MdmSubTask,
    MdmTask)
from mta.runtime.mdm_skuloc_models import (MdmSkuLocAddApproved,
    MdmSkuLocHistory, MdmSkuLocModifyApproved, MdmSkuLocPair,
    MdmSkuLocRemoveApproved)
from mta.serialization import digest, storage
from mta.runtime.mdm_supplier_models import (MdmSobHistory, MdmMoqHistory,
                                            MdmSobRequested, MdmMoqRequested)

SQL_DIGEST = 'c86d014b1f7ee921821f83936a53d1d4da566ba9b2558db9252853260c3c3801'
SCHEMA = 'fresh-mdm-daily-input-v1'
CONSUMER_ORDER = ('skuloc-add', 'sku-description', 'location-description',
    'sku-add', 'location-add', 'location-remove', 'sku-remove',
    'skuloc-remove', 'sku-overlay', 'location-overlay', 'skuloc-overlay')
NMS_DATA_HISTORY_HORIZON = 15  # Engine/StdSettingsPre.bat:86

SKU_FIELDS = tuple(name for name in SKU_ALIASES.values() if name != 'SKUCode')
LOCATION_FIELDS = tuple(name for name in LOCATION_ALIASES.values() if name != 'WHCode')
PAIR_ATTRIBUTES = ('PackSize', 'SpikeThreshold', 'PSOThreshold', 'FGRMFlag',
    'StockPercentForRationing', 'NormPercentReservation',
    *('c%d' % i for i in range(1, 16)))

_SETS = (
    ('sku', 'attributes', MdmSkuAttributes,
     tuple(n for n in SKU_ALIASES.values() if n != 'SKUDescription'), "owner='Importer'"),
    ('sku', 'descriptions', MdmSkuDescription, ('SKUCode', 'SKUDescription'), "owner='Importer'"),
    ('sku', 'approved', MdmSkuApproved,
     (*SKU_ALIASES.values(), 'ActionType', 'Approved', 'Reverted'), None),
    ('location', 'attributes', MdmLocationAttributes,
     tuple(n for n in LOCATION_ALIASES.values() if n != 'WHDescription'), "owner='Importer'"),
    ('location', 'descriptions', MdmLocationDescription,
     ('WHCode', 'WHDescription'), "owner='Importer'"),
    ('location', 'approved', MdmLocationApproved,
     (*LOCATION_ALIASES.values(), 'ActionType', 'Approved', 'Reverted'), None),
    ('skuloc', 'attributes', MdmSkuLocPair,
     ('SKUCode', 'LocCode', *PAIR_ATTRIBUTES), "owner='Importer'"),
    ('skuloc', 'additions', MdmSkuLocAddApproved,
     tuple(f.name for f in MdmSkuLocAddApproved._meta.fields if f.name not in ('id', 'source')), None),
    ('skuloc', 'modifications', MdmSkuLocModifyApproved,
     tuple(f.name for f in MdmSkuLocModifyApproved._meta.fields if f.name not in ('id', 'source')), None),
    ('skuloc', 'removals', MdmSkuLocRemoveApproved,
     ('SKUCode', 'WhCode', 'Approved'), None),
)

_QUEUES = {
    ('sku', 'approved'): MdmSkuApproved,
    ('location', 'approved'): MdmLocationApproved,
    ('skuloc', 'additions'): MdmSkuLocAddApproved,
    ('skuloc', 'modifications'): MdmSkuLocModifyApproved,
    ('skuloc', 'removals'): MdmSkuLocRemoveApproved,
}


def capture_configuration(importer_settings):
    """Resolve scalar native settings required before an MDM capture."""
    # ImportMasterDataComponents.bat:6-27 branches on COUNT(rows whose value
    # is 1), so missing and duplicate false rows are the same inactive case.
    active_count = sum(1 for row in importer_settings
        if sql_key(row.get('Parameter')) == 'nmsactive'
        and sql_key(str(row.get('Value'))) == '1')
    if active_count > 1:
        raise ValueError('canonical NMSActive count is neither zero nor one')
    nms_active = active_count == 1
    task_horizons = [int(row['Value']) for row in importer_settings
                     if row['Parameter'] == 'TaskStatusLogHorizon']
    if len(task_horizons) != 1:
        raise ValueError('exact TaskStatusLogHorizon setting required for MDM daily input')
    return nms_active, task_horizons[0]


def apply_refresh_setting(importer_settings, snapshot):
    """Apply NMSImportData's UpdatePWh marker to the new run's working copy."""
    if not snapshot['nms_active']:
        return
    rows = [row for row in importer_settings
            if row['Parameter'] == 'UpdatePWh_RLT_RCP_GCP']
    if len(rows) != 1:
        raise ValueError('exact UpdatePWh_RLT_RCP_GCP setting required for MDM daily input')
    rows[0]['Value'] = '1' if isinstance(rows[0]['Value'], str) else 1


def _snapshot_sets(source):
    """Read all ten source sets in one PostgreSQL statement snapshot."""
    expressions, params = [], []
    for _family, _kind, model, columns, predicate in _SETS:
        table = connection.ops.quote_name(model._meta.db_table)
        selected_parts = []
        for name in ('id', *columns):
            quoted = connection.ops.quote_name(name)
            field = model._meta.get_field(name)
            # row_to_json would pass NUMERIC through a binary float parser.
            # Text preserves the exact PostgreSQL typmod value and matches the
            # canonical Decimal storage representation used at consumption.
            selected_parts.append((quoted + '::text AS ' + quoted)
                                  if field.get_internal_type() == 'DecimalField'
                                  else quoted)
        selected = ','.join(selected_parts)
        where = 'source_id=%s' + ((' AND ' + predicate) if predicate else '')
        expressions.append("(SELECT coalesce(json_agg(row_to_json(r)),'[]'::json) "
            "FROM (SELECT %s FROM %s WHERE %s ORDER BY id) r)" %
            (selected, table, where))
        params.append(source.pk)
    with connection.cursor() as cursor:
        cursor.execute('SELECT ' + ','.join(expressions), params)
        values = cursor.fetchone()
    result = {'sku': {}, 'location': {}, 'skuloc': {}}
    for (family, kind, _model, _columns, _predicate), rows in zip(_SETS, values):
        result[family][kind] = storage(rows)
    return result


def _revision_digest(source, family, rows):
    clean = {name: [{k: v for k, v in row.items() if k != 'id'} for row in values]
             for name, values in rows.items()}
    return digest({'source_digest': source.digest, 'sql_digest': SQL_DIGEST,
                   'family': family, 'rows': clean})


def _pair_exclusion_digest(rows):
    return digest([{'SKUCode': row.get('SKUCode'), 'WhCode': row.get('WhCode')}
                   for row in rows])


def _validated_pair_exclusions(rows):
    """ValidateExclusions.sql:19-61 final bag after the NMS mutation stage."""
    trimmed = [{'SKUCode': (row.get('SKUCode').strip(' ')
                            if row.get('SKUCode') is not None else None),
                'WhCode': (row.get('WhCode').strip(' ')
                           if row.get('WhCode') is not None else None)}
               for row in rows]
    trimmed = [row for row in trimmed
               if not (row['SKUCode'] is None and row['WhCode'] is None)]
    # One NULL is a native whole-table rejection. An empty bag is retained as
    # an explicitly installed empty source, never inferred from missing rows.
    if any(row['SKUCode'] is None or row['WhCode'] is None for row in trimmed):
        return []
    result = []
    by_key = {}
    for row in trimmed:
        key = (sql_key(row['SKUCode']), sql_key(row['WhCode']))
        previous = by_key.get(key)
        if previous is None:
            by_key[key] = row
            result.append(row)
        elif previous != row:
            # SQL DISTINCT under the deployed case-insensitive collation does
            # not define which differently-cased representative survives.
            raise ValueError('SOURCE_ORDER_AMBIGUITY: exclusion DISTINCT representative')
    return result


def _capture_pair_exclusions(source):
    from mta.runtime.mdm_daily_models import (MdmPairExclusion,
        MdmPairExclusionSource)
    owner = MdmPairExclusionSource.objects.select_for_update().filter(source=source).first()
    if owner is None:
        raise ValueError('pair exclusion source is unavailable; explicit bootstrap required')
    rows = list(MdmPairExclusion.objects.select_for_update().filter(source=source)
                .order_by('ordinal').values('SKUCode', 'WhCode'))
    if owner.row_count != len(rows) or owner.digest != _pair_exclusion_digest(rows):
        raise ValueError('pair exclusion source identity drift')
    if _validated_pair_exclusions(rows) != rows:
        raise ValueError('pair exclusion opening is not the validated canonical bag')
    return {'digest': owner.digest, 'row_count': owner.row_count, 'rows': storage(rows)}


@transaction.atomic
def install_pair_exclusions(source, rows, *, provenance):
    """Install one explicitly supplied, validated opening; never infer empty."""
    import json
    from mta.runtime.mdm_daily_models import MdmPairExclusion, MdmPairExclusionSource
    from mta.runtime.mdm_models import MdmSource
    MdmSource.objects.select_for_update().get(pk=source.pk)
    if (not isinstance(provenance, dict) or not provenance
            or len(json.dumps(provenance)) > 16384):
        raise ValueError('Bounded explicit exclusion provenance required')
    if not isinstance(rows, list) or any(
            not isinstance(row, dict) or set(row) != {'SKUCode', 'WhCode'}
            or any(value is not None and (not isinstance(value, str) or len(value) > 50)
                   for value in row.values()) for row in rows):
        raise ValueError('Canonical pair exclusion fields required')
    if _validated_pair_exclusions(rows) != rows:
        raise ValueError('Opening must already be the validated canonical exclusion bag')
    if (MdmPairExclusionSource.objects.filter(source=source).exists()
            or MdmPairExclusion.objects.filter(source=source).exists()):
        raise ValueError('Pair exclusion opening already installed')
    owner = MdmPairExclusionSource.objects.create(source=source,
        digest=_pair_exclusion_digest(rows), row_count=len(rows), provenance=provenance)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.mdm_pair_bootstrap',%s,true)", [str(source.pk)])
    MdmPairExclusion.objects.bulk_create([MdmPairExclusion(source=source,
        ordinal=ordinal, **row) for ordinal, row in enumerate(rows, 1)])
    return owner


def compose_pair_exclusions(snapshot, incoming_master):
    """Apply NMSImportData 474-499, then ValidateExclusions 19-61."""
    if snapshot['schema'] != SCHEMA or digest({k: v for k, v in snapshot.items()
            if k != 'revision_digest'}) != snapshot['revision_digest']:
        raise ValueError('MDM daily input revision drift')
    result = deepcopy(snapshot)
    opening = deepcopy(result['pair_exclusion_opening']['rows'])
    if not result['nms_active']:
        post_nms = opening
    else:
        if any('SKUCode' not in row or 'WhCode' not in row for row in incoming_master):
            raise ValueError('pair exclusion composition requires MasterDataRaw keys')
        key = lambda row: (sql_key(row.get('SKUCode')), sql_key(row.get('WhCode')))
        initial_keys = {key(row) for row in incoming_master if None not in key(row)}
        candidates = []
        for row in result['rows']['skuloc']['additions']:
            pair_key = key(row)
            if row['Approved'] and row['DBMActive'] is False and pair_key not in initial_keys:
                candidates.append({'SKUCode': row.get('SKUCode'),
                                   'WhCode': row.get('WhCode')})
        modifications = [row for row in result['rows']['skuloc']['modifications']
                         if row['Approved']]
        candidates.extend({'SKUCode': row.get('SKUCode'), 'WhCode': row.get('WhCode')}
                          for row in modifications if row['DBMActive'] is False)
        opening_keys = {key(row) for row in opening if None not in key(row)}
        candidates = [row for row in candidates
            if key(row) not in opening_keys]
        post_nms = [*opening, *candidates]
        enabled = {key(row) for row in modifications
                   if row['DBMActive'] is True and None not in key(row)}
        post_nms = [row for row in post_nms
                    if key(row) not in enabled]
    result['pair_exclusions_post_nms'] = storage(post_nms)
    result['pair_exclusions'] = storage(_validated_pair_exclusions(post_nms))
    result.pop('revision_digest', None)
    result['revision_digest'] = digest(result)
    return storage(result)


def _task_snapshot(source):
    from mta.runtime.mdm_force_models import MdmForceHistory
    from mta.runtime.mdm_season_models import MdmSeasonHistory
    from mta.runtime.mdm_stop_pipo_models import MdmStopPipoHistory
    from mta.runtime.mdm_phase_controls_models import MdmPhaseOutHistory
    # NMSTaskStatusUpdate's Phase In Norm block also reads TaskPhaseOutHistory.
    # Do not silently substitute PhaseInNormHistory to make master9 complete.
    families = (('sku', MdmSkuHistory), ('location', MdmLocationHistory),
                ('skuloc', MdmSkuLocHistory), ('sob', MdmSobHistory), ('moq', MdmMoqHistory),
                ('force', MdmForceHistory), ('season', MdmSeasonHistory), ('stop_pipo', MdmStopPipoHistory),
                ('phase_out', MdmPhaseOutHistory))
    result = []
    for family, history_model in families:
        approved = list(history_model.objects.filter(source=source, Status='3')
                        .values('id', 'TaskId').order_by('id'))
        by_task = {}
        for row in approved:
            by_task.setdefault(row['TaskId'], []).append(row['id'])
        for task_id, history_ids in by_task.items():
            tasks = list(MdmTask.objects.filter(source=source, TaskID=task_id).order_by('id'))
            if len(tasks) != 1:
                raise ValueError('canonical MDM task status UPDATE has ambiguous task header')
            task = tasks[0]
            history_digest = digest(history_ids)
            for sub in MdmSubTask.objects.filter(source=source, TaskID=task_id,
                                                  TaskStatus__in=('2', '3')).order_by('id'):
                task_values = {'task_pk': task.pk, 'task_id': task_id,
                    'action_type': task.Actiontype, 'subtask_pk': sub.pk,
                    'subtask_status': sub.TaskStatus, 'history_ids': history_ids}
                result.append({**task_values, 'family': family,
                    'task_digest': digest(task_values), 'history_digest': history_digest})
    return result


def select_capture(source, *, nms_active, task_status_log_horizon):
    """Freeze one eligible revision; caller owns an atomic source-row lock."""
    if type(nms_active) is not bool:
        raise ValueError('NMSActive must be explicit')
    if type(task_status_log_horizon) is not int:
        raise ValueError('TaskStatusLogHorizon must be an explicit integer')
    from mta.mdm.supplier_revisions import lock_transaction
    lock_transaction(source.pk)
    source = MdmSource.objects.select_for_update().get(pk=source.pk)
    from mta.mdm.integration_source import capture_identity, verify_capture
    integration = capture_identity(source)
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    if MdmDailyInputCapture.objects.filter(source=source, status='CAPTURED',
                                           retries__isnull=True).exists():
        raise ValueError('MDM source already has an unconsumed daily capture; retry it explicitly')
    # ImportMasterDataComponents supplies one $(RunDateTime) to both
    # NMSArchiveInputData.sql:9-10 and NMSTaskStatusUpdate.sql:15-16. Freeze it
    # before reading this revision so long calculations and retries retain the
    # same native archive/task timestamp.
    run_timestamp = database_now()
    pair_exclusion_opening = _capture_pair_exclusions(source)
    rows = (_snapshot_sets(source) if nms_active else
        {'sku': {'attributes': [], 'descriptions': [], 'approved': []},
         'location': {'attributes': [], 'descriptions': [], 'approved': []},
         'skuloc': {'attributes': [], 'additions': [], 'modifications': [], 'removals': []}})
    revisions = {family: _revision_digest(source, family, rows[family])
                 for family in ('sku', 'location', 'skuloc')}
    occurrences = []
    for family, kind, _model, _columns, _predicate in _SETS:
        if (family, kind) not in _QUEUES:
            continue
        for ordinal, row in enumerate(rows[family][kind]):
            values = {k: v for k, v in row.items() if k != 'id'}
            occurrences.append({'family': family, 'queue_kind': kind,
                'source_pk': row['id'], 'ordinal': ordinal,
                'sku_code': row.get('SKUCode'),
                'location_code': row.get('WhCode'),
                'action_type': row.get('ActionType'), 'approved': bool(row['Approved']),
                'reverted': row.get('Reverted'), 'row_digest': digest(values)})
    snapshot = {'schema': SCHEMA, 'source_id': source.pk,
        'source_digest': source.digest, 'sql_digest': SQL_DIGEST,
        'nms_active': nms_active, 'consumer_order': list(CONSUMER_ORDER),
        'configuration': {'nms_data_history_horizon': NMS_DATA_HISTORY_HORIZON,
                          'task_status_log_horizon': task_status_log_horizon,
                          'run_timestamp': storage(run_timestamp)},
        'revision_digests': revisions, 'rows': rows,
        'pair_exclusion_opening': pair_exclusion_opening,
        'pair_exclusions_post_nms': deepcopy(pair_exclusion_opening['rows']),
        'pair_exclusions': deepcopy(pair_exclusion_opening['rows']),
        'occurrences': occurrences,
        # NMSTaskStatusUpdate runs later in the main BAT even when NMSActive=0.
        'tasks': _task_snapshot(source), 'history_transitions': [],
        'completion_tasks': [], 'prune_tasks': []}
    from mta.mdm.supplier_capture import capture as capture_supplier
    supplier = capture_supplier(source)
    if supplier is not None:
        snapshot['supplier'] = supplier
    from mta.mdm.force_capture import capture as capture_force
    force = capture_force(source)
    if force is not None:
        snapshot['force'] = force
    from mta.mdm.season_capture import capture as capture_season
    season = capture_season(source)
    if season is not None:
        snapshot['season'] = season
    from mta.mdm.stop_pipo_capture import capture as capture_stop
    stop = capture_stop(source)
    if stop is not None:
        snapshot['stop_pipo'] = stop
    from mta.mdm.phase_controls_capture import capture as capture_phase
    phase = capture_phase(source)
    if phase is not None:
        snapshot['phase_controls'] = phase
    if integration is not None:
        snapshot['integration'] = integration
    verify_capture(source, snapshot)
    snapshot['revision_digest'] = digest(snapshot)
    return storage(snapshot)


def capture_pending_conflicts(snapshot, source, composed_rows):
    """Freeze native pending-Add 'Already in Vectorflow' history identities."""
    result = deepcopy(snapshot)
    sku_keys = {sql_key(row.get('SKUCode')) for row in composed_rows if row.get('SKUCode') is not None}
    location_keys = {sql_key(row.get('WhCode')) for row in composed_rows if row.get('WhCode') is not None}
    pair_keys = {(sql_key(row.get('SKUCode')), sql_key(row.get('WhCode')))
                 for row in composed_rows if row.get('SKUCode') is not None and row.get('WhCode') is not None}
    transitions = []
    for family, history_model, key in (
            ('sku', MdmSkuHistory, lambda row: sql_key(row.SKUCode)),
            ('location', MdmLocationHistory, lambda row: sql_key(row.WHCode)),
            ('skuloc', MdmSkuLocHistory,
             lambda row: (sql_key(row.SKUCode), sql_key(row.WhCode)))):
        members = {'sku': sku_keys, 'location': location_keys, 'skuloc': pair_keys}[family]
        task_ids = set(MdmTask.objects.filter(source=source, MasterId={'sku': '1',
            'location': '2', 'skuloc': '3'}[family], Actiontype=1,
            TaskID__in=MdmSubTask.objects.filter(source=source, TaskStatus__in=('1', '8'))
                .values('TaskID')).values_list('TaskID', flat=True))
        for row in history_model.objects.filter(source=source, TaskId__in=task_ids).order_by('id'):
            if key(row) not in members: continue
            values = {field.name: storage(getattr(row, field.name)) for field in row._meta.fields
                      if field.name not in ('id', 'source')}
            transitions.append({'family': family, 'history_pk': row.pk,
                'task_id': row.TaskId, 'row_digest': digest(values)})
    result['history_transitions'] = transitions
    result.pop('revision_digest', None)
    result['revision_digest'] = digest(result)
    return storage(result)


def _prune_models(master_id):
    from mta.runtime.mdm_force_models import MdmForceHistory, MdmForceRequested
    from mta.runtime.mdm_season_models import (MdmSeasonHistory, MdmSeasonRequested,
        MdmSeasonStatusHistory, MdmSeasonStatusRequested)
    from mta.runtime.mdm_models import MdmLocationRequested, MdmSkuRequested
    from mta.runtime.mdm_skuloc_models import (MdmSkuLocAddRequested,
        MdmSkuLocModifyRequested, MdmSkuLocRemoveRequested)
    from mta.runtime.mdm_stop_pipo_models import MdmStopPipoHistory, MdmStopPipoRequested
    from mta.runtime.mdm_phase_controls_models import (MdmPhaseOutHistory,
        MdmPhaseOutRequested, MdmPhaseInNormHistory, MdmPhaseInNormRequested)
    return {'6': (MdmStopPipoHistory, MdmStopPipoRequested),
            '7': (MdmPhaseOutHistory, MdmPhaseOutRequested),
            '8': (MdmPhaseOutHistory, MdmPhaseOutRequested),
            '9': (MdmPhaseInNormHistory, MdmPhaseInNormRequested),
            '1': (MdmSkuHistory, MdmSkuRequested),
            '2': (MdmLocationHistory, MdmLocationRequested),
            '3': (MdmSkuLocHistory, MdmSkuLocAddRequested,
                  MdmSkuLocModifyRequested, MdmSkuLocRemoveRequested),
            '4': (MdmSobHistory, MdmSobRequested),
            '5': (MdmMoqHistory, MdmMoqRequested),
            '10': (MdmSeasonStatusHistory, MdmSeasonStatusRequested),
            '11': (MdmSeasonHistory, MdmSeasonRequested),
            '12': (MdmSeasonHistory, MdmSeasonRequested),
            '13': (MdmForceHistory, MdmForceRequested)}[master_id]


def _model_identity(model):
    return model._meta.label_lower


def _row_version(row):
    values = {field.name: storage(getattr(row, field.name)) for field in row._meta.fields
              if field.name not in ('id', 'source')}
    return {'pk': row.pk, 'digest': digest(values)}


def capture_prune_candidates(snapshot, source, business_date):
    """Freeze native completed-task retention candidates and every owned row."""
    result = deepcopy(snapshot)
    cutoff = datetime.combine(business_date - timedelta(days=
        result['configuration']['task_status_log_horizon']), time.min,
        tzinfo=database_now().tzinfo)
    candidates = []; completions = []
    projected = {row['subtask_pk']: ('4' if row['subtask_status'] == '2' else '5')
                 for row in result['tasks']}
    for task in MdmTask.objects.filter(source=source,
            MasterId__in=('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13')).order_by('id'):
        subtasks = list(MdmSubTask.objects.filter(source=source,
                                                  TaskID=task.TaskID).order_by('id'))
        statuses = [projected.get(row.pk, row.TaskStatus) for row in subtasks]
        if not statuses or not all(value in ('4', '5', '6', '8') for value in statuses):
            continue
        completion = {'task_id': task.TaskID, 'master_id': task.MasterId, 'task': _row_version(task),
            'subtasks': [_row_version(row) for row in subtasks],
            'projected_statuses': statuses}
        completion['digest'] = digest({k: v for k, v in completion.items()
                                       if k != 'digest'})
        completions.append(completion)
        if task.PendingSince is None or task.PendingSince > cutoff:
            continue
        members = {_model_identity(MdmTask): [_row_version(task)]}
        members[_model_identity(MdmSubTask)] = [_row_version(row) for row in subtasks]
        for model in _prune_models(task.MasterId):
            members[_model_identity(model)] = [_row_version(row) for row in
                model.objects.filter(source=source, TaskId=task.TaskID).order_by('id')]
        candidates.append({'task_id': task.TaskID, 'master_id': task.MasterId,
                           'members': members, 'digest': digest(members)})
    result['completion_tasks'] = completions
    result['prune_tasks'] = candidates
    result.pop('revision_digest', None)
    result['revision_digest'] = digest(result)
    return storage(result)


def _lock_prune_candidates(snapshot, capture, *, deferred_tasks=()):
    model_by_label = {_model_identity(MdmTask): MdmTask,
                      _model_identity(MdmSubTask): MdmSubTask}
    for master_id in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13'):
        model_by_label.update({_model_identity(model): model
                               for model in _prune_models(master_id)})
    locked = []
    for candidate in snapshot['prune_tasks']:
        if (int(candidate['master_id']), candidate['task_id']) in deferred_tasks:
            continue
        if digest(candidate['members']) != candidate['digest']:
            raise ValueError('captured MDM task-prune roster drift')
        candidate_rows = []
        for label, identities in candidate['members'].items():
            model = model_by_label[label]
            field = 'TaskID' if model in (MdmTask, MdmSubTask) else 'TaskId'
            current = list(model.objects.select_for_update().filter(source=capture.source,
                **{field: candidate['task_id']}).order_by('id'))
            if ([row.pk for row in current] != [item['pk'] for item in identities]
                    or [_row_version(row)['digest'] for row in current] !=
                       [item['digest'] for item in identities]):
                raise ValueError('captured MDM task-prune rows changed before consumption')
            candidate_rows.append((model, [row.pk for row in current]))
        locked.append(candidate_rows)
    return locked


def _lock_completion_candidates(snapshot, capture, *, deferred_tasks=()):
    locked = []
    for candidate in snapshot['completion_tasks']:
        if (int(candidate.get('master_id', 0)), candidate['task_id']) in deferred_tasks:
            continue
        expected = {k: v for k, v in candidate.items() if k != 'digest'}
        if digest(expected) != candidate['digest']:
            raise ValueError('captured MDM task-completion roster drift')
        task = MdmTask.objects.select_for_update().filter(source=capture.source,
            pk=candidate['task']['pk'], TaskID=candidate['task_id']).first()
        subtasks = list(MdmSubTask.objects.select_for_update().filter(source=capture.source,
            TaskID=candidate['task_id']).order_by('id'))
        if (task is None or _row_version(task)['digest'] != candidate['task']['digest']
                or [row.pk for row in subtasks] != [item['pk'] for item in candidate['subtasks']]
                or [_row_version(row)['digest'] for row in subtasks] !=
                   [item['digest'] for item in candidate['subtasks']]):
            raise ValueError('captured MDM task-completion rows changed before consumption')
        locked.append((task.pk, [row.pk for row in subtasks], candidate['projected_statuses']))
    return locked


def _unique(rows, keys, label):
    matches = [row for row in rows if all(sql_key(row.get(k)) == sql_key(v)
                                         for k, v in keys.items())]
    clean = [{k: v for k, v in row.items() if k != 'id'} for row in matches]
    if clean and any(row != clean[0] for row in clean[1:]):
        raise ValueError('canonical %s UPDATE has incomparable duplicate source values' % label)
    return clean[0] if clean else None


def compose(snapshot, master_rows, *, last_run_date, master_columns=RAW_COLUMNS):
    """Apply the qualified MasterDataRaw statements in their native order."""
    result = deepcopy(list(master_rows))
    if snapshot['schema'] != SCHEMA or digest({k: v for k, v in snapshot.items()
            if k != 'revision_digest'}) != snapshot['revision_digest']:
        raise ValueError('MDM daily input revision drift')
    if not snapshot['nms_active']:
        return result
    if tuple(master_columns) != tuple(RAW_COLUMNS) or any(set(row) != set(master_columns) for row in result):
        raise ValueError('composed MDM input requires complete MasterDataRaw columns')
    rows = snapshot['rows']; blank = lambda: dict.fromkeys(master_columns)
    pair = lambda row, wh='WhCode': (sql_key(row.get('SKUCode')), sql_key(row.get(wh)))

    # NMSNewItems is staged and anti-joined before any standalone additions.
    existing = {pair(row) for row in result}
    pair_adds = [row for row in rows['skuloc']['additions']
                 if row['Approved'] and pair(row) not in existing]
    for staged in pair_adds:
        row = blank()
        for name in ('SKUCode', 'WhCode', 'Norm', 'MinNorm', 'RLT', 'RCP', 'GCP',
                     'OCP', 'ParentWhCode', 'PackSize', 'SpikeThreshold', 'PSOThreshold',
                     'FGRMFlag', 'NormPercentReservation', 'MinOrderCount'):
            row[name] = staged[name]
        row['SKUIntroDate'] = last_run_date
        row['StockPercentForRationing'] = staged['StockPercentForRat']
        result.append(row)

    sku_codes = {sql_key(row.get('SKUCode')) for row in result}
    additions = []
    for staged in rows['sku']['descriptions']:
        if sql_key(staged['SKUCode']) not in sku_codes:
            row = {**blank(), 'SKUCode': staged['SKUCode'],
                   'SKUDescription': staged['SKUDescription']}
            if row not in additions: additions.append(row)  # SELECT DISTINCT
    result.extend(additions)
    location_codes = {sql_key(row.get('WhCode')) for row in result}
    additions = []
    for staged in rows['location']['descriptions']:
        if sql_key(staged['WHCode']) not in location_codes:
            row = {**blank(), 'WhCode': staged['WHCode'],
                   'WHDescription': staged['WHDescription']}
            additions.append(row)  # Native SiteDescription insert has no DISTINCT.
    result.extend(additions)

    sku_codes = {sql_key(row.get('SKUCode')) for row in result}
    additions = []
    for staged in rows['sku']['approved']:
        if staged['Approved'] and staged['ActionType'] == 1 and sql_key(staged['SKUCode']) not in sku_codes:
            row = {**blank(), **{k: staged[k] for k in ('SKUCode', 'SKUDescription',
                'ElephantOrderCapping', 'Weight', 'Volume', *('SL%d' % i for i in range(1, 6)))}}
            if row not in additions: additions.append(row)  # SELECT DISTINCT
    result.extend(additions)
    location_codes = {sql_key(row.get('WhCode')) for row in result}
    for staged in rows['location']['approved']:  # native statement has no DISTINCT
        if staged['Approved'] and staged['ActionType'] == 1 and sql_key(staged['WHCode']) not in location_codes:
            result.append({**blank(), 'WhCode': staged['WHCode'], **{k: staged[k] for k in
                ('WHDescription', 'LocationType', 'LogisticsLocation',
                 *('LL%d' % i for i in range(1, 6)))}})

    removed_locations = {sql_key(r['WHCode']) for r in rows['location']['approved']
                         if r['Approved'] and r['ActionType'] == 0 and r['WHCode'] is not None}
    result = [r for r in result if r.get('WhCode') is None or sql_key(r['WhCode']) not in removed_locations]
    removed_skus = {sql_key(r['SKUCode']) for r in rows['sku']['approved']
                    if r['Approved'] and r['ActionType'] == 0 and r['SKUCode'] is not None}
    result = [r for r in result if r.get('SKUCode') is None or sql_key(r['SKUCode']) not in removed_skus]
    removed_pairs = {pair(r) for r in rows['skuloc']['removals'] if r['Approved']
                     and r['SKUCode'] is not None and r['WhCode'] is not None}
    result = [r for r in result if pair(r) not in removed_pairs]

    sku_overlay = [r for r in rows['sku']['approved'] if r['Approved'] and r['ActionType'] == 1]
    for row in result:
        if row.get('SKUCode') is None: continue
        key = {'SKUCode': row['SKUCode']}
        attr = _unique(rows['sku']['attributes'], key, 'SKU')
        desc = _unique(rows['sku']['descriptions'], key, 'SKU')
        approved = _unique(sku_overlay, key, 'SKU')
        for name in SKU_FIELDS:
            target = 'SKUAtt' + name[1:].zfill(2) if name.startswith('c') else name
            if approved is not None: row[target] = approved[name]
            elif name == 'SKUDescription': row[target] = desc[name] if desc is not None else None
            elif attr is not None: row[target] = attr[name]
            elif name.startswith('c'): row[target] = None

    location_overlay = [r for r in rows['location']['approved'] if r['Approved'] and r['ActionType'] == 1]
    location_master = {sql_key(r['WHCode']) for r in
                       (*rows['location']['descriptions'], *rows['location']['approved'])}
    for row in result:
        if row.get('WhCode') is None or sql_key(row['WhCode']) not in location_master: continue
        key = {'WHCode': row['WhCode']}
        attr = _unique(rows['location']['attributes'], key, 'Location')
        desc = _unique(rows['location']['descriptions'], key, 'Location')
        approved = _unique(location_overlay, key, 'Location')
        for name in LOCATION_FIELDS:
            target = 'LocAtt' + name[1:].zfill(2) if name.startswith('c') else name
            if approved is not None: row[target] = approved[name]
            elif name == 'WHDescription': row[target] = desc[name] if desc is not None else None
            elif attr is not None: row[target] = attr[name]

    pair_modify = [r for r in rows['skuloc']['modifications'] if r['Approved']]
    core = ('ParentWhCode', 'MinNorm', 'RLT', 'RCP', 'GCP', 'OCP', 'MinOrderCount')
    pair_core = {}
    for row in result:
        current_pair = pair(row)
        if None in current_pair: continue
        values = tuple(row.get(name) for name in core)
        if current_pair in pair_core and pair_core[current_pair] != values:
            raise ValueError('canonical SKULocMaster DISTINCT join is incomparable')
        pair_core[current_pair] = values
    for row in result:
        if None in pair(row): continue
        keys = {'SKUCode': row['SKUCode'], 'LocCode': row['WhCode']}
        attr = _unique(rows['skuloc']['attributes'], keys, 'SKU-location')
        added = _unique(pair_adds, {'SKUCode': row['SKUCode'], 'WhCode': row['WhCode']}, 'SKU-location')
        modified = _unique(pair_modify, {'SKUCode': row['SKUCode'], 'WhCode': row['WhCode']}, 'SKU-location')
        if attr is not None:
            for name in ('PackSize', 'SpikeThreshold', 'PSOThreshold', 'FGRMFlag',
                         'StockPercentForRationing', 'NormPercentReservation'):
                row[name] = attr[name]
            for i in range(1, 16): row['SKULocAtt%02d' % i] = attr['c%d' % i]
        if added is not None:
            for name in ('PackSize', 'SpikeThreshold', 'PSOThreshold', 'FGRMFlag',
                         'NormPercentReservation', *('SKULocAtt%02d' % i for i in range(1, 16))):
                row[name] = added[name]
            row['StockPercentForRationing'] = added['StockPercentForRat']
        if modified is not None:
            for name in ('ParentWhCode', 'MinNorm', 'RLT', 'RCP', 'GCP', 'PackSize',
                         'FGRMFlag', 'NormPercentReservation', 'MinOrderCount', 'OCP',
                         *('SKULocAtt%02d' % i for i in range(1, 16))):
                if modified[name] is not None: row[name] = modified[name]
            row['SpikeThreshold'] = modified['SpikeThreshold']
            row['PSOThreshold'] = modified['PSOThreshold']
            if modified['StockPercentForRat'] is not None:
                row['StockPercentForRationing'] = modified['StockPercentForRat']
    # The pinned script normalizes location descriptions before rebuilding the
    # parent description after pair modifications.  Its final LEFT JOIN writes
    # ND for both NULL and unknown parents.
    for row in result:
        if row.get('WHDescription') is None:
            row['WHDescription'] = 'ND'
        parent = row.get('ParentWhCode')
        parent_row = None
        if parent is not None and sql_key(parent) in location_master:
            key = {'WHCode': parent}
            description = _unique(rows['location']['descriptions'], key, 'Location')
            approved = _unique(location_overlay, key, 'Location')
            parent_row = approved if approved is not None else description
        row['ParentDescription'] = (parent_row['WHDescription']
                                    if parent_row is not None and parent_row.get('WHDescription') is not None
                                    else 'ND')
    return result


def bind_capture(run, snapshot, *, request_digest, origin=None):
    from mta.runtime.mdm_daily_models import (MdmDailyInputCapture,
        MdmDailyInputHistory, MdmDailyInputOccurrence, MdmDailyInputTask,
        MdmDailyPairExclusion)
    capture = MdmDailyInputCapture.objects.create(run=run,
        source_id=snapshot['source_id'], origin=origin, request_digest=request_digest,
        revision_digest=snapshot['revision_digest'], sql_digest=snapshot['sql_digest'],
        nms_active=snapshot['nms_active'],
        sku_revision_digest=snapshot['revision_digests']['sku'],
        location_revision_digest=snapshot['revision_digests']['location'],
        skuloc_revision_digest=snapshot['revision_digests']['skuloc'])
    MdmDailyInputOccurrence.objects.bulk_create([MdmDailyInputOccurrence(
        capture=capture, **row) for row in snapshot['occurrences']])
    MdmDailyInputTask.objects.bulk_create([MdmDailyInputTask(capture=capture,
        family=row['family'], task_id=row['task_id'], task_pk=row['task_pk'],
        subtask_pk=row['subtask_pk'], action_type=row['action_type'],
        prior_subtask_status=row['subtask_status'], task_digest=row['task_digest'],
        history_digest=row['history_digest']) for row in snapshot['tasks']])
    MdmDailyInputHistory.objects.bulk_create([MdmDailyInputHistory(capture=capture,
        **row) for row in snapshot['history_transitions']])
    MdmDailyPairExclusion.objects.bulk_create([MdmDailyPairExclusion(
        capture=capture, ordinal=ordinal, SKUCode=row.get('SKUCode'),
        WhCode=row.get('WhCode'))
        for ordinal, row in enumerate(snapshot['pair_exclusions'], 1)])
    return capture


def _lock_pair_exclusion_opening(snapshot, capture):
    from mta.runtime.mdm_daily_models import (MdmDailyPairExclusion,
        MdmPairExclusion, MdmPairExclusionSource)
    owner = MdmPairExclusionSource.objects.select_for_update().get(source=capture.source)
    current = list(MdmPairExclusion.objects.select_for_update()
                   .filter(source=capture.source).order_by('ordinal')
                   .values('SKUCode', 'WhCode'))
    opening = snapshot['pair_exclusion_opening']
    if (owner.digest != opening['digest'] or owner.row_count != opening['row_count']
            or current != opening['rows'] or _pair_exclusion_digest(current) != owner.digest):
        raise ValueError('captured pair exclusion opening changed before consumption')
    typed = list(MdmDailyPairExclusion.objects.select_for_update()
                 .filter(capture=capture).order_by('ordinal')
                 .values('SKUCode', 'WhCode'))
    if typed != snapshot['pair_exclusions']:
        raise ValueError('typed daily pair exclusion state differs from capture')
    return owner, typed


def finalize_consumption(run, *, output=None):
    """Idempotently consume exactly the frozen rows inside finish_run's atomic block."""
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.mdm.supplier_revisions import lock_transaction, superseded_tasks
    source_id = MdmDailyInputCapture.objects.filter(run=run).values_list('source_id', flat=True).first()
    if source_id is None: return
    lock_transaction(source_id)
    capture = MdmDailyInputCapture.objects.select_for_update().get(run=run, source_id=source_id)
    if capture is None: return
    if capture.status == 'CONSUMED': return
    if run.status != 'RUNNING':
        raise ValueError('MDM consumption must precede successful run publication')
    from mta.runtime.validation_storage import read_input
    snapshot = read_input(run, components=('mdm_input',)).get('mdm_input')
    if not snapshot or snapshot['revision_digest'] != capture.revision_digest:
        raise ValueError('MDM capture/run input identity drift')
    from mta.mdm.integration_source import verify_capture
    verify_capture(capture.source, snapshot)
    deferred_supplier_tasks = superseded_tasks(snapshot)
    from mta.mdm.force_revisions import superseded_tasks as superseded_force_tasks
    deferred_supplier_tasks |= superseded_force_tasks(snapshot)
    from mta.mdm.season_revisions import superseded_tasks as superseded_season_tasks
    deferred_supplier_tasks |= superseded_season_tasks(snapshot)
    from mta.mdm.stop_pipo_revisions import superseded_tasks as superseded_stop_tasks
    deferred_supplier_tasks |= superseded_stop_tasks(snapshot)
    from mta.mdm.phase_controls_revisions import superseded_tasks as superseded_phase_tasks
    deferred_supplier_tasks |= superseded_phase_tasks(snapshot)
    exclusion_owner, final_exclusions = _lock_pair_exclusion_opening(snapshot, capture)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.mdm_consuming_run',%s,true)", [str(run.pk)])
    from mta.mdm.supplier_capture import finalize as finalize_supplier
    finalize_supplier(run, snapshot, output)
    from mta.mdm.force_capture import finalize as finalize_force
    finalize_force(run, snapshot, output)
    from mta.mdm.season_capture import finalize as finalize_season
    finalize_season(run, snapshot, output)
    from mta.mdm.stop_pipo_capture import finalize as finalize_stop
    finalize_stop(run, snapshot, output)
    from mta.mdm.phase_controls_capture import finalize as finalize_phase
    finalize_phase(run, snapshot, output)
    now = database_now()
    run_timestamp = datetime.fromisoformat(snapshot['configuration']['run_timestamp'])
    archive_models = None
    if capture.nms_active:
        from mta.runtime.mdm_daily_models import (MdmDailyLocationArchive,
            MdmDailySkuArchive, MdmDailySkuLocAddArchive,
            MdmDailySkuLocModifyArchive, MdmDailySkuLocRemoveArchive)
        archive_models = {('sku', 'approved'): MdmDailySkuArchive,
            ('location', 'approved'): MdmDailyLocationArchive,
            ('skuloc', 'additions'): MdmDailySkuLocAddArchive,
            ('skuloc', 'modifications'): MdmDailySkuLocModifyArchive,
            ('skuloc', 'removals'): MdmDailySkuLocRemoveArchive}
        archive_cutoff = run.business_date - timedelta(days=
            snapshot['configuration']['nms_data_history_horizon'])
        for archive_model in archive_models.values():
            archive_model.objects.filter(source=capture.source,
                Input_Date__date__lte=archive_cutoff).delete()
    by_identity = {(o.family, o.queue_kind, o.source_pk): o
                   for o in capture.occurrences.select_for_update().all()}
    snapshot_rows = {(o['family'], o['queue_kind'], o['source_pk']): o
                     for o in snapshot['occurrences']}
    if set(by_identity) != set(snapshot_rows):
        raise ValueError('MDM captured occurrence roster drift')
    for key, occurrence in by_identity.items():
        model = _QUEUES[(occurrence.family, occurrence.queue_kind)]
        current = model.objects.select_for_update().filter(
            source=capture.source, pk=occurrence.source_pk).first()
        if current is None:
            raise ValueError('captured MDM queue occurrence disappeared before consumption')
        fields = next(columns for family, kind, _m, columns, _p in _SETS
                      if (family, kind) == (occurrence.family, occurrence.queue_kind))
        current_values = storage({name: getattr(current, name) for name in fields})
        if digest(current_values) != occurrence.row_digest:
            raise ValueError('captured MDM queue occurrence changed before consumption')
        if capture.nms_active:
            archive_model = archive_models[(occurrence.family, occurrence.queue_kind)]
            archive_model.objects.create(source=capture.source, occurrence=occurrence,
                Input_Date=run_timestamp, **current_values)
        occurrence.archived_at = now
        if occurrence.approved:
            current.delete(); occurrence.cleared_at = now
        occurrence.save(update_fields=['archived_at', 'cleared_at'])

    completion_rows = _lock_completion_candidates(snapshot, capture, deferred_tasks=deferred_supplier_tasks)
    prune_rows = _lock_prune_candidates(snapshot, capture, deferred_tasks=deferred_supplier_tasks)
    stamp = run_timestamp.strftime('%d/%m/%Y %I:%M%p')
    captured_tasks = {row['subtask_pk']: row for row in snapshot['tasks']}
    for item in capture.task_occurrences.select_for_update().all():
        if item.family == 'phase_out' and any((mid, item.task_id) in deferred_supplier_tasks for mid in (7, 8, 9)):
            continue
        if item.family == 'season' and any((mid, item.task_id) in deferred_supplier_tasks for mid in (11, 12)):
            continue
        if item.family in ('sob', 'moq', 'force', 'stop_pipo') and (
                {'sob': 4, 'moq': 5, 'force': 13, 'stop_pipo': 6}[item.family], item.task_id) in deferred_supplier_tasks:
            continue
        task = MdmTask.objects.filter(source=capture.source, pk=item.task_pk,
                                      TaskID=item.task_id).first()
        sub = MdmSubTask.objects.filter(source=capture.source, pk=item.subtask_pk,
                                        TaskID=item.task_id).first()
        from mta.runtime.mdm_force_models import MdmForceHistory
        from mta.runtime.mdm_season_models import MdmSeasonHistory
        from mta.runtime.mdm_stop_pipo_models import MdmStopPipoHistory
        from mta.runtime.mdm_phase_controls_models import MdmPhaseOutHistory
        history_model = {'sku': MdmSkuHistory, 'location': MdmLocationHistory,
                         'skuloc': MdmSkuLocHistory, 'sob': MdmSobHistory,
                         'moq': MdmMoqHistory, 'force': MdmForceHistory, 'season': MdmSeasonHistory,
                         'stop_pipo': MdmStopPipoHistory, 'phase_out': MdmPhaseOutHistory}[item.family]
        captured = captured_tasks.get(item.subtask_pk)
        if captured is None:
            raise ValueError('MDM captured task roster drift')
        history_ids = captured['history_ids']
        current_history_ids = list(history_model.objects.filter(source=capture.source,
            TaskId=item.task_id, Status='3', pk__in=history_ids).order_by('id')
            .values_list('id', flat=True))
        values = {'task_pk': task.pk if task else None, 'task_id': item.task_id,
            'action_type': task.Actiontype if task else None,
            'subtask_pk': sub.pk if sub else None,
            'subtask_status': sub.TaskStatus if sub else None, 'history_ids': history_ids}
        if task is None or sub is None or digest(values) != item.task_digest \
                or current_history_ids != history_ids or digest(history_ids) != item.history_digest:
            raise ValueError('captured MDM task transition changed before consumption')
        new_status = '4' if sub.TaskStatus == '2' else '5'
        sub.TaskStatus = new_status; sub.DBUpdatedDate = stamp
        sub.save(update_fields=['TaskStatus', 'DBUpdatedDate'])
        item.transitioned_at = now; item.save(update_fields=['transitioned_at'])
    for task_pk, subtask_pks, projected_statuses in completion_rows:
        statuses = list(MdmSubTask.objects.filter(pk__in=subtask_pks).order_by('id')
                        .values_list('TaskStatus', flat=True))
        if statuses != projected_statuses:
            raise ValueError('captured MDM task completion differs after transitions')
        MdmTask.objects.filter(source=capture.source, pk=task_pk).update(TaskStatus='7')
    history_models = {'sku': MdmSkuHistory, 'location': MdmLocationHistory,
                      'skuloc': MdmSkuLocHistory}
    for item in capture.history_occurrences.select_for_update().all():
        model = history_models[item.family]
        row = model.objects.filter(source=capture.source, pk=item.history_pk,
                                   TaskId=item.task_id).first()
        if row is None:
            raise ValueError('captured pending Add history disappeared before consumption')
        values = {field.name: storage(getattr(row, field.name)) for field in row._meta.fields
                  if field.name not in ('id', 'source')}
        if digest(values) != item.row_digest:
            raise ValueError('captured pending Add history changed before consumption')
        row.Status = '4'; row.Comments = 'Already in Vectorflow'
        row.save(update_fields=['Status', 'Comments'])
        item.transitioned_at = now; item.save(update_fields=['transitioned_at'])

    from mta.mdm.supplier_capture import finalize_pending as finalize_supplier_pending
    finalize_supplier_pending(snapshot, output, deferred_tasks=deferred_supplier_tasks)
    for candidate_rows in prune_rows:
        # Header is first in the roster and therefore deleted last.
        for model, pks in reversed(candidate_rows):
            model.objects.filter(pk__in=pks).delete()
    from mta.runtime.mdm_daily_models import MdmPairExclusion
    MdmPairExclusion.objects.filter(source=capture.source).delete()
    MdmPairExclusion.objects.bulk_create([MdmPairExclusion(
        source=capture.source, ordinal=ordinal, SKUCode=row.get('SKUCode'),
        WhCode=row.get('WhCode'))
        for ordinal, row in enumerate(final_exclusions, 1)])
    exclusion_owner.digest = _pair_exclusion_digest(final_exclusions)
    exclusion_owner.row_count = len(final_exclusions)
    exclusion_owner.save(update_fields=['digest', 'row_count'])
    capture.status = 'CONSUMED'; capture.consumed_at = now
    capture.save(update_fields=['status', 'consumed_at'])
