"""Finite pre-BTR consumers of actual accepted typed BPR, not UI acceptance."""
import json
import os
import unittest
from unittest.mock import patch

from tests import test_scoped_pick_files_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedReportsTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','bpr'):
        locals()[_name]=getattr(fixtures.ScopedPickFileTests,_name)

    def test_all_reports_use_actual_phase_inputs_without_full_publication_or_replay(self):
        from mta.presentation.scoped_reports import produce,recipe_digest
        from mta.presentation.scoped_sources import bind
        from mta.presentation import excess,fulfillment,expedite,pick_post,rrr
        from mta.runtime.models import RunPhaseAcceptance,ScopePickFiles,DailyReportGeneration
        from mta.serialization import storage,digest
        self.bpr()
        before=list(RunPhaseAcceptance.objects.filter(run=self.run).values_list('id','digest'))
        self.run.refresh_from_db()
        p=self.phase;s=self.sources;today=self.run.business_date.isoformat()
        rationed=storage(p.late['vf_RationedReqReport']);standards=storage(p.standard_attributes)
        pick=storage(rrr.pick_rows(rationed,s.pick_bands))
        expected=dict(
            ExcessInventoryDetails=excess.produce(rationed,standards,today),
            OrderFulfillmentSummary=fulfillment.produce_summary(rationed,standards),
            OrderFulfillmentDetails=fulfillment.produce_details(storage(p.order_state['SpikeOrderData']),
                storage(s.routes),standards,today),
            ExpediteDispatches=expedite.produce_before_btr(pick,storage(p.importer['MasterData']),standards,rationed),
            PickPost=pick_post.produce(pick))
        with patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('BPR replay')), \
                patch('mta.temporal.chain.produce_dbm',side_effect=AssertionError('DBM replay')), \
                patch('mta.presentation.operational_reports.prepare',side_effect=AssertionError('Full publication')):
            metadata,rows=produce(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        self.assertEqual(rows,expected)
        self.assertTrue(rows['OrderFulfillmentSummary']);self.assertTrue(rows['OrderFulfillmentDetails'])
        self.assertTrue(rows['PickPost']);self.assertTrue(rows['ExpediteDispatches'])
        self.assertEqual(metadata['source_digest'],bind(self.receipt.pk,
            expected_digest=self.receipt.digest,action_revision=0).source_digest)
        self.assertEqual(metadata['recipe_digest'],recipe_digest())
        self.assertEqual(metadata['phase_id'],str(self.receipt.pk))
        self.assertEqual(metadata['images'],{name:dict(count=len(bag),digest=digest(bag)) for name,bag in rows.items()})
        self.assertTrue(all(row[field] is None for row in rows['ExpediteDispatches'] for field in expedite.AGE_FIELDS))
        self.assertEqual(list(RunPhaseAcceptance.objects.filter(run=self.run).values_list('id','digest')),before)
        self.assertFalse(ScopePickFiles.objects.filter(phase__run=self.run).exists())
        self.assertFalse(DailyReportGeneration.objects.filter(run=self.run).exists())
        self.run.refresh_from_db();self.assertEqual(self.run.status,'RUNNING');self.assertFalse(self.run.output_digest)
        print(json.dumps(dict(status='ACCEPTED_BPR_REPORT_ROWS_MATCH_ORIGINAL_PRODUCER_INPUTS',
            images=metadata['images'],expedite_age_fields='NULL_BEFORE_BTR')),flush=True)

    def test_wrong_owner_or_revision_is_denied_before_report_production(self):
        from mta.presentation.scoped_reports import produce
        from mta.presentation.context import PublicationUnavailable
        self.bpr()
        with patch('mta.presentation.excess.produce',side_effect=AssertionError('unadmitted producer')):
            for phase,checksum,revision in ((self.pre_receipt.pk,self.pre_receipt.digest,0),
                    (self.receipt.pk,'f'*64,0),(self.receipt.pk,self.receipt.digest,1)):
                with self.subTest(phase=phase,revision=revision),self.assertRaises(PublicationUnavailable):
                    produce(phase,expected_digest=checksum,action_revision=revision)


if __name__=='__main__':unittest.main()
