"""Immutable accepted facts and a revision-bound native preparation receipt.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
from uuid import UUID
from django.db import connection, transaction
from mta.serialization import canonical_parts, digest
from mta.row_sequences import RecordRows
from mta.runtime import batch_storage
from mta.runtime.ingestion_admission import EPOCHS

CONTRACT = 'vectorflow-accepted-daily-v1'


def parameters(value):
    return {k: str(v) if isinstance(v, UUID) else v for k, v in value.items()}


def epochs(initialization_id, *, lock=False):
    from mta.runtime.ingestion_models import IngestionRevisionState
    rows = IngestionRevisionState.objects
    if lock:
        rows = rows.select_for_update()
    row = rows.values(*EPOCHS).get(initialization_id=initialization_id)
    return [row[name] for name in EPOCHS]


def split(value, intake):
    """Keep only structural/scalar metadata; every fact bag has a typed owner."""
    from mta.application.production_csv_contract import feeds
    paths = {v['path']: name for name, v in feeds(intake).items()}
    if value['consumer_opening'] is not None:
        paths.update({batch_storage.TABLES[name]['path'].replace('consumer/', 'consumer_opening/', 1): name
                      for name in batch_storage.DECLARATION['internal_roster']})
    populations = {}
    def pack(item, path):
        if path in paths:
            name = paths[path]
            populations[name] = (RecordRows(len(item), lambda item=item: (dict(row) for row in item))
                                 if len(item) > 10000 else item)
            return {'population': name}
        if isinstance(item, dict):
            return {'object': [[k, pack(v, path+'/'+k if path else k)] for k, v in item.items()]}
        if isinstance(item, list):
            if (path == 'producer_sources/report_policy/output_contract/boroa_text/fields'
                    and item == list(__import__('mta.application.production_output_policy',
                        fromlist=['ATTRIBUTES']).ATTRIBUTES)):
                return {'names': item}
            if item:
                raise ValueError('Unowned accepted daily population: '+path)
            return {'empty': True}
        return {'scalar': item}
    tree = pack(value, '')
    if set(populations) != set(paths.values()):
        raise ValueError('Accepted daily fact roster is incomplete')
    return tree, populations


def join(tree, populations):
    def unpack(node):
        if set(node) == {'population'}:
            return list(populations[node['population']])
        if set(node) == {'object'}:
            return {k: unpack(v) for k, v in node['object']}
        if set(node) == {'empty'} and node['empty'] is True:
            return []
        if set(node) == {'names'}:
            return list(node['names'])
        if set(node) == {'scalar'}:
            return node['scalar']
        raise ValueError('Accepted daily structural receipt differs')
    return unpack(tree)


def seal(attempt, prepared, arguments, readiness):
    """The source lock plus revision row serializes intake against live writers."""
    from mta.mdm.supplier_revisions import source_lock
    from mta.runtime.daily_feed_models import DailyFeedAttempt
    value = prepared.checked(attempt.input_sha256)
    intake = value.get('intake_schema', value['schema'])
    tree, populations = split(value, intake)
    with source_lock(attempt.initialization.source_id), transaction.atomic():
        current = DailyFeedAttempt.objects.select_for_update().get(pk=attempt.pk)
        before = epochs(attempt.initialization_id, lock=True)
        if (tuple(before) != readiness.revisions.as_tuple() or current.accepted_facts
                or current.prepared_context or current.status != 'RUNNING' or current.phase != 'VALIDATE'):
            raise ValueError('Daily preparation changed during native inspection')
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.daily_batch',%s,true)", [str(attempt.attempt_id)])
        manifest = batch_storage.save_populations(attempt, intake, populations)
        cut = epochs(attempt.initialization_id)
        cut[2] += 1  # Exactly the following single attempt UPDATE, guarded in SQL.
        body = dict(contract=CONTRACT, attempt_id=str(attempt.attempt_id),
            initialization_id=str(attempt.initialization_id), source_digest=readiness.source_digest,
            input_sha256=attempt.input_sha256, batch_digest=attempt.batch_digest,
            certification_digest=readiness.certification_digest,
            master_revision_id=readiness.master_revision_id, configuration_digest=readiness.configuration_digest,
            parameters=parameters(arguments), revisions=cut, facts_digest=digest(manifest), tree=tree)
        body['receipt_digest'] = digest(body)
        if sum(map(len, canonical_parts(body))) > 262144:
            raise ValueError('Accepted daily preparation metadata exceeds its bound')
        attempt.accepted_facts, attempt.prepared_context = manifest, body
        attempt.certification_id = __import__('mta.runtime.ingestion_models', fromlist=['InitializationCertification']).InitializationCertification.objects.get(
            initialization_id=attempt.initialization_id, status='CERTIFIED').pk
        attempt.master_revision_id = readiness.master_revision_id
        attempt.phase = 'VALIDATED'
        attempt.save(update_fields=['accepted_facts','prepared_context','certification','master_revision','phase','updated_at'])
        if epochs(attempt.initialization_id) != cut:
            raise ValueError('Accepted daily revision cut did not seal atomically')
    return attempt


def check(attempt, arguments, *, locked=False):
    body = attempt.prepared_context
    if (not isinstance(body, dict) or body.get('contract') != CONTRACT
            or body.get('receipt_digest') != digest({k:v for k,v in body.items() if k != 'receipt_digest'})
            or body.get('attempt_id') != str(attempt.attempt_id)
            or body.get('initialization_id') != str(attempt.initialization_id)
            or body.get('input_sha256') != attempt.input_sha256
            or body.get('batch_digest') != attempt.batch_digest
            or body.get('source_digest') != attempt.initialization.source.digest
            or body.get('parameters') != parameters(arguments)
            or body.get('facts_digest') != digest(attempt.accepted_facts)
            or body.get('master_revision_id') != str(attempt.master_revision_id)
            or attempt.certification.receipt_digest != body.get('certification_digest')
            or attempt.certification.status != 'CERTIFIED'
            or attempt.master_revision.status != 'ACCEPTED'
            or attempt.status != 'RUNNING' or attempt.phase != 'VALIDATED' or attempt.run_id is not None):
        raise ValueError('Accepted daily preparation authority differs')
    if epochs(attempt.initialization_id, lock=locked) != body['revisions']:
        raise ValueError('Accepted daily preparation is stale; revalidation requires explicit reconciliation')
    from mta.runtime.ingestion_admission import preparation_readiness, _admit, _process_release
    if locked:
        import os
        release = _process_release(os.environ.get('VF_NATIVE_RELEASE_COMMIT'), os.environ.get('VF_NATIVE_RELEASE_SHA256'))
        with connection.cursor() as cursor:
            current = _admit(cursor, attempt.initialization_id, release, pending=True)
    else:
        current = preparation_readiness(attempt.initialization_id)
    if (current.certification_digest != body['certification_digest']
            or current.master_revision_id != body['master_revision_id']
            or current.configuration_digest != body['configuration_digest']):
        raise ValueError('Accepted daily current release/certification differs')
    return body


def read(attempt, arguments):
    body = check(attempt, arguments)
    populations = batch_storage.read_populations(attempt)
    value = join(body['tree'], populations)
    checksum = hashlib.sha256()
    for part in canonical_parts(value, ensure_ascii=False):
        checksum.update(part)
    if checksum.hexdigest() != attempt.input_sha256:
        raise ValueError('Accepted daily full typed reconstruction differs')
    from mta.runtime.daily_preparation import restored
    return restored(value, attempt.input_sha256, body)


def references(attempt):
    from mta.runtime.input_v3 import BATCH_PATHS
    entries = {item['filename']: item for item in attempt.accepted_facts['feeds']}
    return {path: dict(attempt_id=str(attempt.attempt_id), filename=name,
        manifest_digest=digest(attempt.accepted_facts), population_digest=entries[name]['digest'],
        count=entries[name]['count']) for path, name in BATCH_PATHS.items() if name in entries}
