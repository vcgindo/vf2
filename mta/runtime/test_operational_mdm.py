"""Pure fixture proof for read-only operational MDM qualification."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mta.mdm.daily_input import CONSUMER_ORDER, SCHEMA, SQL_DIGEST, _revision_digest
from mta.presentation import operational_mdm
from mta.serialization import digest


STAMP = datetime(2026, 10, 9, 8, 30, tzinfo=timezone.utc)


class FixtureRows:
    """Minimal immutable QuerySet-shaped projection for fixture comparisons."""
    def __init__(self, rows):
        self.rows = deepcopy(rows)

    def order_by(self, *_fields):
        return self

    def values(self, *fields):
        return [{field: row[field] for field in fields} for row in self.rows]


def capture_fixture(*, occurrences=(), tasks=(), histories=(), exclusions=()):
    return SimpleNamespace(
        consumed_at=STAMP,
        occurrences=FixtureRows(occurrences),
        task_occurrences=FixtureRows(tasks),
        history_occurrences=FixtureRows(histories),
        mdmdailypairexclusion_set=FixtureRows(exclusions),
    )


class OperationalMdmCaptureFixtureTests(SimpleTestCase):
    """Full immutable-child comparisons without a database or business run."""

    def test_populated_ordered_capture_and_transition_stamps(self):
        occurrence_values = [
            {'family': 'sku', 'queue_kind': 'approved', 'source_pk': 11,
             'ordinal': 0, 'sku_code': 'A', 'location_code': None,
             'action_type': 2, 'approved': True, 'reverted': False,
             'row_digest': 'a' * 64},
            {'family': 'skuloc', 'queue_kind': 'modifications', 'source_pk': 12,
             'ordinal': 0, 'sku_code': 'B', 'location_code': 'L',
             'action_type': None, 'approved': False, 'reverted': None,
             'row_digest': 'b' * 64},
        ]
        occurrences = [
            {**occurrence_values[0], 'archived_at': STAMP, 'cleared_at': STAMP},
            {**occurrence_values[1], 'archived_at': STAMP, 'cleared_at': None},
        ]
        history_ids = [31, 32]
        task_values = {'task_pk': 21, 'task_id': 'TASK', 'action_type': 2,
                       'subtask_pk': 22, 'subtask_status': '2',
                       'history_ids': history_ids}
        task = {'family': 'sku', **task_values,
                'task_digest': digest(task_values),
                'history_digest': digest(history_ids)}
        typed_task = {
            'family': 'sku', 'task_id': 'TASK', 'task_pk': 21,
            'subtask_pk': 22, 'action_type': 2, 'prior_subtask_status': '2',
            'task_digest': task['task_digest'],
            'history_digest': task['history_digest'], 'transitioned_at': STAMP,
        }
        history = {'family': 'sku', 'history_pk': 41, 'task_id': 'ADD',
                   'row_digest': 'c' * 64}
        typed_history = {**history, 'transitioned_at': STAMP}
        exclusions = [{'SKUCode': 'A', 'WhCode': 'L1'},
                      {'SKUCode': 'B', 'WhCode': 'L2'}]
        typed_exclusions = [
            {'ordinal': 1, **exclusions[0]},
            {'ordinal': 2, **exclusions[1]},
        ]
        capture = capture_fixture(occurrences=occurrences, tasks=[typed_task],
                                  histories=[typed_history],
                                  exclusions=typed_exclusions)
        snapshot = {'occurrences': occurrence_values, 'tasks': [task],
                    'history_transitions': [history],
                    'pair_exclusions': exclusions}

        self.assertEqual(operational_mdm._verify_occurrences(capture, snapshot),
                         digest(occurrence_values))
        self.assertEqual(operational_mdm._verify_tasks(capture, snapshot),
                         digest([{key: value for key, value in task.items()
                                  if key != 'history_ids'}]))
        self.assertEqual(operational_mdm._verify_histories(capture, snapshot),
                         digest([history]))
        self.assertEqual(operational_mdm._verify_pair_exclusions(capture, snapshot),
                         digest(exclusions))

    def test_changed_row_ordinal_and_stamp_are_denied(self):
        expected = {'family': 'sku', 'queue_kind': 'approved', 'source_pk': 11,
                    'ordinal': 0, 'sku_code': 'A', 'location_code': None,
                    'action_type': 2, 'approved': True, 'reverted': False,
                    'row_digest': 'a' * 64}
        changed = {**expected, 'source_pk': 99, 'archived_at': STAMP,
                   'cleared_at': STAMP}
        capture = capture_fixture(occurrences=[changed])
        with self.assertRaisesRegex(ValueError, 'occurrence roster/order'):
            operational_mdm._verify_occurrences(
                capture, {'occurrences': [expected]})

        capture = capture_fixture(exclusions=[
            {'ordinal': 2, 'SKUCode': 'A', 'WhCode': 'L'}])
        with self.assertRaisesRegex(ValueError, 'ordinal roster'):
            operational_mdm._verify_pair_exclusions(
                capture, {'pair_exclusions': [{'SKUCode': 'A', 'WhCode': 'L'}]})

        history_ids = [31]
        values = {'task_pk': 21, 'task_id': 'TASK', 'action_type': 2,
                  'subtask_pk': 22, 'subtask_status': '2',
                  'history_ids': history_ids}
        expected_task = {'family': 'sku', **values,
                         'task_digest': digest(values),
                         'history_digest': digest(history_ids)}
        typed_task = {
            'family': 'sku', 'task_id': 'TASK', 'task_pk': 21,
            'subtask_pk': 22, 'action_type': 2, 'prior_subtask_status': '2',
            'task_digest': expected_task['task_digest'],
            'history_digest': expected_task['history_digest'],
            'transitioned_at': STAMP.replace(minute=31),
        }
        capture = capture_fixture(tasks=[typed_task])
        with self.assertRaisesRegex(ValueError, 'transition stamp'):
            operational_mdm._verify_tasks(capture, {'tasks': [expected_task]})


class OperationalMdmFullFixtureTests(SimpleTestCase):
    """Full verifier fixture: no SQL is executed and no owner is mutated."""

    def build(self, *, source_id=7):
        source = SimpleNamespace(pk=7, digest='d' * 64,
            database_name='fixture_db',
            receipt={'database': 'fixture_db'})
        rows = {'sku': {}, 'location': {}, 'skuloc': {}}
        revisions = {family: _revision_digest(source, family, rows[family])
                     for family in rows}
        snapshot = {
            'schema': SCHEMA, 'source_id': source_id,
            'source_digest': source.digest, 'sql_digest': SQL_DIGEST,
            'nms_active': False, 'consumer_order': list(CONSUMER_ORDER),
            'revision_digests': revisions, 'rows': rows,
            'occurrences': [], 'tasks': [], 'history_transitions': [],
            'pair_exclusions': [],
        }
        snapshot['revision_digest'] = digest(snapshot)
        raw = {'mdm_input': snapshot}
        run = SimpleNamespace(pk='run-fixture', input_digest=digest(raw))
        capture = capture_fixture()
        capture.source = source
        capture.origin = None
        capture.status = 'CONSUMED'
        capture.source_id = source.pk
        capture.request_digest = 'r' * 64
        capture.revision_digest = snapshot['revision_digest']
        capture.sku_revision_digest = revisions['sku']
        capture.location_revision_digest = revisions['location']
        capture.skuloc_revision_digest = revisions['skuloc']
        capture.sql_digest = SQL_DIGEST
        capture.nms_active = False
        return run, raw, capture

    def verify(self, run, raw, capture):
        manager = MagicMock()
        manager.select_related.return_value.filter.return_value.first.return_value = capture
        cursor = MagicMock()
        cursor.fetchone.return_value = ('fixture_db',)
        context = MagicMock()
        context.__enter__.return_value = cursor
        context.__exit__.return_value = False
        fixture_connection = SimpleNamespace(cursor=MagicMock(return_value=context))
        with patch.object(operational_mdm.MdmDailyInputCapture, 'objects', manager), \
                patch.object(operational_mdm, 'connection', fixture_connection), \
                patch.object(operational_mdm, '_verify_installed_owners',
                             return_value=({'1': {}, '2': {}, '3': {}}, [])):
            return operational_mdm.verify_consumed(run, raw, {'schema': 'fixture'})

    def test_valid_empty_capture_returns_read_only_digest_metadata(self):
        run, raw, capture = self.build()
        result = self.verify(run, raw, capture)
        self.assertEqual((result['run'], result['source'], result['database']),
                         ('run-fixture', 7, 'fixture_db'))
        self.assertEqual(result['digest'],
                         digest({key: value for key, value in result.items()
                                 if key != 'digest'}))

    def test_missing_or_changed_source_and_revision_are_denied(self):
        run, raw, capture = self.build()
        with self.assertRaisesRegex(ValueError, 'capture is unavailable'):
            self.verify(run, raw, None)

        run, raw, capture = self.build(source_id=None)
        with self.assertRaisesRegex(ValueError, 'source identity'):
            self.verify(run, raw, capture)

        run, raw, capture = self.build(source_id=8)
        with self.assertRaisesRegex(ValueError, 'source identity'):
            self.verify(run, raw, capture)

        run, raw, capture = self.build()
        capture.revision_digest = '0' * 64
        with self.assertRaisesRegex(ValueError, 'revision identity'):
            self.verify(run, raw, capture)


class OperationalMdmInstallationFixtureTests(SimpleTestCase):
    """The immutable opening slice is distinct from later live appends."""

    def test_supported_append_is_ignored_but_original_ordinal_mutation_denies(self):
        class MutableOwner:
            pass

        class OwnerManager:
            def __init__(self, rows):
                self.rows = rows

            def filter(self, **kwargs):
                limit = kwargs['ordinal__lte']
                return FixtureRows([row for row in self.rows
                                    if row['ordinal'] <= limit])

        artifact = {'schema': 'fixture-artifact-v1'}
        expected = [{'Code': 'OPENING'}]
        batches = [(1, MutableOwner, {'owner': 'Importer'}, expected,
                    '/case/opening/owner')]
        field = SimpleNamespace(name='Code')
        MutableOwner.objects = OwnerManager([
            {'ordinal': 1, 'Code': 'OPENING'},
            {'ordinal': 2, 'Code': 'LATER-APPEND'},
        ])
        with patch.object(operational_mdm, 'owners', return_value=batches), \
                patch.object(operational_mdm, 'business_fields',
                             return_value=[field]):
            _, families = operational_mdm._expected_installation(artifact)
            source = SimpleNamespace(receipt={
                'artifact_schema': artifact['schema'], 'families': families})
            _, readback = operational_mdm._verify_installed_owners(source, artifact)
            self.assertEqual(readback[0]['rows'], 1)

            MutableOwner.objects = OwnerManager([
                {'ordinal': 1, 'Code': 'MUTATED'},
                {'ordinal': 2, 'Code': 'LATER-APPEND'},
            ])
            with self.assertRaisesRegex(ValueError, 'typed readback differs'):
                operational_mdm._verify_installed_owners(source, artifact)
