import json
from datetime import datetime, timezone

from django.test import TestCase

from mta.presentation import ancillary_live
from mta.presentation.context import PublicationUnavailable
from mta.runtime.models import CalculationRun
from mta.serialization import digest


class DailyRemarkOwnershipTests(TestCase):
    def run(self, result=None):
        # These tables are imported into the app by the owning migration before
        # this focused PostgreSQL test is run.
        return super().run(result)

    def _run(self, raw):
        return CalculationRun.objects.create(
            kind='DAILY_CHAIN', status='RUNNING', business_date='2026-10-06',
            input_digest=digest(raw), execution_revision=self._testMethodName,
            input_payload=raw, production_manifest={'images': {}})

    def test_raw_snapshot_is_retry_stable_and_serving_adds_only_later_events(self):
        receipt = {'version': 1, 'origin': 'explicit-empty-BPR-owner'}
        ancillary_live.initialize_owner(
            ancillary_live.BPR, provenance_digest=digest(receipt),
            provenance_receipt=receipt)
        first = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)
        ancillary_live.append(ancillary_live.BPR, [dict(
            SKUCode='S1', WhCode='W1', Remark=None, Username='requester')],
            actor_id='3', timestamp=first)

        raw_snapshot = json.loads(json.dumps(ancillary_live.snapshot_all(
            business_date='2026-10-06', bpr_remark_horizon=90)))
        self.assertEqual(set(raw_snapshot), {ancillary_live.BPR})
        run = self._run({'remark_inputs': raw_snapshot})
        bound = ancillary_live.bind_snapshots(run, raw_snapshot)
        self.assertEqual(bound[ancillary_live.PATHS[ancillary_live.BPR]]['count'], 1)

        second = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)
        ancillary_live.append(ancillary_live.BPR, [dict(
            SKUCode='S1', WhCode='W1', Remark='later', Username='reviewer')],
            actor_id='2', timestamp=second)
        path = ancillary_live.PATHS[ancillary_live.BPR]
        self.assertEqual([row['Remark'] for row in ancillary_live.image_rows(run, path)], [None])
        self.assertEqual([row['Remark'] for row in ancillary_live.image_rows(
            run, path, include_live=True)], [None, 'later'])
        query, params = ancillary_live.image_query(run, path, include_live=True)
        self.assertIn(' UNION ALL ', query)
        self.assertEqual(params[-3:-1], [ancillary_live.BPR, 1])
        self.assertEqual(ancillary_live.bind_snapshots(run, raw_snapshot), bound)

        changed = json.loads(json.dumps(raw_snapshot))
        changed[ancillary_live.BPR]['rows'][0]['Remark'] = 'changed'
        with self.assertRaises(PublicationUnavailable):
            ancillary_live.bind_snapshots(run, changed)

    def test_missing_owner_is_absent_but_initialized_empty_owner_is_captured(self):
        self.assertEqual(ancillary_live.snapshot_all(business_date='2026-10-06'), {})
        receipt = {'version': 1, 'origin': 'explicit-empty-BOR-owner'}
        ancillary_live.initialize_owner(
            ancillary_live.BOR, provenance_digest=digest(receipt),
            provenance_receipt=receipt)
        snapshots = ancillary_live.snapshot_all(business_date='2026-10-06')
        self.assertEqual(set(snapshots), {ancillary_live.BOR})
        self.assertEqual(snapshots[ancillary_live.BOR]['rows'], [])
        run = self._run({'remark_inputs': snapshots})
        ancillary_live.bind_snapshots(run, snapshots)
        self.assertEqual(ancillary_live.image_rows(
            run, ancillary_live.PATHS[ancillary_live.BOR]), [])

    def test_bpr_cutoff_excludes_boundary_but_preserves_journal_highwater(self):
        receipt = {'version': 1, 'origin': 'retention-boundary-BPR-owner'}
        ancillary_live.initialize_owner(
            ancillary_live.BPR, provenance_digest=digest(receipt),
            provenance_receipt=receipt)
        cutoff = datetime(2026, 10, 6, tzinfo=timezone.utc)
        ancillary_live.append(ancillary_live.BPR, [
            dict(SKUCode='S0', WhCode='W0', Remark='boundary', Username='u'),
        ], actor_id='3', timestamp=cutoff)
        ancillary_live.append(ancillary_live.BPR, [
            dict(SKUCode='S1', WhCode='W1', Remark='retained', Username='u'),
        ], actor_id='3', timestamp=cutoff.replace(second=1))
        snapshot = ancillary_live.snapshot_all(
            business_date='2026-10-06', bpr_remark_horizon=0)[ancillary_live.BPR]
        self.assertEqual(snapshot['watermark'], 2)
        self.assertEqual([row['source_ordinal'] for row in snapshot['rows']], [1])
        future_cutoff = ancillary_live.snapshot_all(
            business_date='2026-10-06', bpr_remark_horizon=-1)[ancillary_live.BPR]
        self.assertEqual(future_cutoff['cutoff'], '2026-10-07T00:00:00+00:00')
        self.assertEqual(future_cutoff['rows'], [])
        run = self._run({'remark_inputs': {ancillary_live.BPR: snapshot}})
        ancillary_live.bind_snapshot(run, ancillary_live.BPR, snapshot)
        self.assertEqual([row['Remark'] for row in ancillary_live.image_rows(
            run, ancillary_live.PATHS[ancillary_live.BPR])], ['retained'])
        ancillary_live.append(ancillary_live.BPR, [
            dict(SKUCode='S2', WhCode='W2', Remark='later-boundary', Username='u'),
        ], actor_id='3', timestamp=cutoff)
        ancillary_live.append(ancillary_live.BPR, [
            dict(SKUCode='S3', WhCode='W3', Remark='later-retained', Username='u'),
        ], actor_id='3', timestamp=cutoff.replace(second=2))
        self.assertEqual([row['Remark'] for row in ancillary_live.image_rows(
            run, ancillary_live.PATHS[ancillary_live.BPR], include_live=True)],
            ['retained', 'later-retained'])
        query, params = ancillary_live.image_query(
            run, ancillary_live.PATHS[ancillary_live.BPR], include_live=True)
        self.assertIn('"RemarkDate">%s', query)
        self.assertEqual(params[-1], cutoff)
