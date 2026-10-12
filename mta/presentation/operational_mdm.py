"""Read-only qualification of the MDM input consumed by one daily run."""
from django.db import connection

from mta.mdm.daily_input import (CONSUMER_ORDER, SCHEMA, SQL_DIGEST,
                                 _revision_digest)
from mta.mdm.daily_source_install import business_fields, owners
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.serialization import digest, storage


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _expected_installation(artifact):
    """Rebuild the install receipt and typed opening ordinal slices."""
    families = {str(master_id): {'owners': []} for master_id in (1, 2, 3)}
    batches = owners(artifact)
    for family, model, kwargs, rows, path in batches:
        fields = [field.name for field in business_fields(model)]
        families[str(family)]['owners'].append({
            'model': model.__name__,
            **kwargs,
            'input_path': path,
            'rows': len(rows),
            'digest': digest(storage(rows)),
            'fields': fields,
        })
    return batches, families


def _verify_installed_owners(source, artifact, run=None):
    try:
        batches, expected_families = _expected_installation(artifact)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('MDM artifact cannot define the installed owners') from exc

    receipt = source.receipt
    _require(isinstance(receipt, dict), 'MDM source receipt is unavailable')
    _require(receipt.get('artifact_schema') == artifact.get('schema'),
             'MDM source artifact schema differs')
    _require(receipt.get('families') == expected_families,
             'MDM installed owner receipt differs from the exact artifact')

    from mta.mdm.daily_source import APPROVAL_DAY_ARTIFACT_SHA
    if receipt.get('artifact_sha256') == APPROVAL_DAY_ARTIFACT_SHA:
        _require(run is not None, 'Active current verification requires its run')
        from mta.mdm.daily_current import verify_published
        return expected_families, verify_published(run, source)

    readback = []
    for family, model, kwargs, expected, path in batches:
        fields = [field.name for field in business_fields(model)]
        # Application MDM owners are live and may append later workflow state.
        # The installation receipt is the immutable full-opening evidence; this
        # read verifies the original typed ordinal slice without asserting that
        # the mutable owner's current full bag still equals its opening bag.
        actual = list(model.objects.filter(source=source, **kwargs,
                            ordinal__lte=len(expected)).order_by('ordinal')
                      .values('ordinal', *fields))
        ordinals = [row.pop('ordinal') for row in actual]
        _require(ordinals == list(range(1, len(expected) + 1)),
                 'MDM installed owner ordinal readback differs: ' + path)
        _require(storage(actual) == storage(expected),
                 'MDM installed owner typed readback differs: ' + path)
        readback.append({'family': family, 'model': model.__name__, **kwargs,
                         'input_path': path, 'rows': len(actual),
                         'digest': digest(storage(actual))})
    return expected_families, readback


def _verify_origin(capture):
    origin = capture.origin
    if origin is None:
        return None
    immutable = ('source_id', 'request_digest', 'revision_digest',
                 'sku_revision_digest', 'location_revision_digest',
                 'skuloc_revision_digest', 'sql_digest', 'nms_active')
    _require(all(getattr(origin, name) == getattr(capture, name)
                 for name in immutable),
             'MDM retry origin identity differs from the consumed capture')
    _require(origin.run.status == 'FAILED' and origin.status == 'CAPTURED'
             and origin.consumed_at is None,
             'MDM retry origin is not the retained failed capture')
    return str(origin.pk)


def _verify_occurrences(capture, snapshot):
    expected = snapshot.get('occurrences')
    _require(isinstance(expected, list), 'MDM occurrence capture is unavailable')
    fields = ('family', 'queue_kind', 'source_pk', 'ordinal', 'sku_code',
              'location_code', 'action_type', 'approved', 'reverted',
              'row_digest')
    _require(all(isinstance(row, dict) and set(row) == set(fields)
                 for row in expected), 'MDM occurrence capture fields differ')
    actual = list(capture.occurrences.order_by('id').values(*fields,
                  'archived_at', 'cleared_at'))
    values = [{name: row[name] for name in fields} for row in actual]
    _require(storage(values) == storage(expected),
             'MDM consumed occurrence roster/order differs')
    for row in actual:
        _require(row['archived_at'] == capture.consumed_at,
                 'MDM consumed occurrence archive stamp differs')
        expected_clear = capture.consumed_at if row['approved'] else None
        _require(row['cleared_at'] == expected_clear,
                 'MDM consumed occurrence clear stamp differs')
    return digest(storage(values))


def _verify_tasks(capture, snapshot):
    expected = snapshot.get('tasks')
    _require(isinstance(expected, list), 'MDM task capture is unavailable')
    expected_fields = ('family', 'task_id', 'task_pk', 'subtask_pk',
                       'action_type', 'subtask_status', 'history_ids',
                       'task_digest', 'history_digest')
    _require(all(isinstance(row, dict)
                 and set(expected_fields) == set(row) for row in expected),
             'MDM task capture fields differ')
    for row in expected:
        task_values = {name: row[name] for name in (
            'task_pk', 'task_id', 'action_type', 'subtask_pk',
            'subtask_status', 'history_ids')}
        _require(digest(task_values) == row['task_digest']
                 and digest(row['history_ids']) == row['history_digest'],
                 'MDM task capture digest differs')
    actual = list(capture.task_occurrences.order_by('id').values(
        'family', 'task_id', 'task_pk', 'subtask_pk', 'action_type',
        'prior_subtask_status', 'task_digest', 'history_digest',
        'transitioned_at'))
    values = [{
        'family': row['family'], 'task_id': row['task_id'],
        'task_pk': row['task_pk'], 'subtask_pk': row['subtask_pk'],
        'action_type': row['action_type'],
        'subtask_status': row['prior_subtask_status'],
        'task_digest': row['task_digest'],
        'history_digest': row['history_digest'],
    } for row in actual]
    expected_values = [{name: row[name] for name in (
        'family', 'task_id', 'task_pk', 'subtask_pk', 'action_type',
        'subtask_status', 'task_digest', 'history_digest')}
        for row in expected]
    _require(storage(values) == storage(expected_values),
             'MDM consumed task roster/order differs')
    _require(all(row['transitioned_at'] == capture.consumed_at for row in actual),
             'MDM consumed task transition stamp differs')
    return digest(storage(values))


def _verify_histories(capture, snapshot):
    expected = snapshot.get('history_transitions')
    _require(isinstance(expected, list), 'MDM history capture is unavailable')
    fields = ('family', 'history_pk', 'task_id', 'row_digest')
    _require(all(isinstance(row, dict) and set(row) == set(fields)
                 for row in expected), 'MDM history capture fields differ')
    actual = list(capture.history_occurrences.order_by('id').values(
        *fields, 'transitioned_at'))
    values = [{name: row[name] for name in fields} for row in actual]
    _require(storage(values) == storage(expected),
             'MDM consumed history roster/order differs')
    _require(all(row['transitioned_at'] == capture.consumed_at for row in actual),
             'MDM consumed history transition stamp differs')
    return digest(storage(values))


def _verify_pair_exclusions(capture, snapshot):
    expected = snapshot.get('pair_exclusions')
    _require(isinstance(expected, list),
             'MDM daily pair exclusion capture is unavailable')
    _require(all(isinstance(row, dict)
                 and set(row) == {'SKUCode', 'WhCode'} for row in expected),
             'MDM daily pair exclusion fields differ')
    actual = list(capture.mdmdailypairexclusion_set.order_by('ordinal')
                  .values('ordinal', 'SKUCode', 'WhCode'))
    ordinals = [row.pop('ordinal') for row in actual]
    _require(ordinals == list(range(1, len(expected) + 1)),
             'MDM daily pair exclusion ordinal roster differs')
    _require(storage(actual) == storage(expected),
             'MDM daily pair exclusion rows differ')
    return digest(storage(actual))


def verify_consumed(run, raw, artifact):
    """Verify persisted MDM consumption evidence without changing any owner."""
    _require(isinstance(raw, dict) and digest(raw) == run.input_digest,
             'Daily raw input identity differs')
    snapshot = raw.get('mdm_input')
    _require(isinstance(snapshot, dict) and snapshot.get('schema') == SCHEMA,
             'MDM daily input capture is unavailable or unsupported')
    revision = snapshot.get('revision_digest')
    _require(isinstance(revision, str) and
             digest({key: value for key, value in snapshot.items()
                     if key != 'revision_digest'}) == revision,
             'MDM daily input revision digest differs')

    capture = (MdmDailyInputCapture.objects.select_related('source', 'origin__run')
               .filter(run=run).first())
    _require(capture is not None, 'MDM input capture is unavailable')
    source = capture.source
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        database = cursor.fetchone()[0]
    _require(isinstance(source.receipt, dict)
             and database == source.database_name == source.receipt.get('database'),
             'MDM source database identity differs')

    _require(capture.status == 'CONSUMED' and capture.consumed_at is not None,
             'MDM input capture is not consumed')
    _require(snapshot.get('source_id') == source.pk
             and snapshot.get('source_digest') == source.digest,
             'MDM capture source identity differs')
    _require(snapshot.get('sql_digest') == capture.sql_digest == SQL_DIGEST,
             'MDM capture SQL identity differs')
    _require(revision == capture.revision_digest,
             'MDM capture revision identity differs')
    revisions = snapshot.get('revision_digests')
    _require(isinstance(revisions, dict) and set(revisions) == {
        'sku', 'location', 'skuloc'}, 'MDM family revision roster differs')
    _require((revisions['sku'], revisions['location'], revisions['skuloc']) ==
             (capture.sku_revision_digest, capture.location_revision_digest,
              capture.skuloc_revision_digest),
             'MDM family revision identities differ')
    rows = snapshot.get('rows')
    _require(isinstance(rows, dict) and set(rows) == {
        'sku', 'location', 'skuloc'}, 'MDM family row roster differs')
    try:
        computed_revisions = {family: _revision_digest(source, family, rows[family])
                              for family in revisions}
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError('MDM family rows cannot define a revision') from exc
    _require(revisions == computed_revisions, 'MDM family revision content differs')
    _require(snapshot.get('consumer_order') == list(CONSUMER_ORDER),
             'MDM consumer order differs')
    _require(snapshot.get('nms_active') is capture.nms_active,
             'MDM NMS activation identity differs')

    families, owner_readback = _verify_installed_owners(source, artifact, run)
    origin = _verify_origin(capture)
    evidence = {
        'schema': 'fresh-operational-mdm-verification-v1',
        'run': str(run.pk),
        'source': source.pk,
        'source_digest': source.digest,
        'database': database,
        'origin': origin,
        'revision_digest': revision,
        'sql_digest': capture.sql_digest,
        'family_receipt_digest': digest(families),
        'owner_readback_digest': digest(owner_readback),
        'occurrence_digest': _verify_occurrences(capture, snapshot),
        'task_digest': _verify_tasks(capture, snapshot),
        'history_digest': _verify_histories(capture, snapshot),
        'pair_exclusion_digest': _verify_pair_exclusions(capture, snapshot),
        'consumed_at': storage(capture.consumed_at),
    }
    evidence['digest'] = digest(evidence)
    return evidence
