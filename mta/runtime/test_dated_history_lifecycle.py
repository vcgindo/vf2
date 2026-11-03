"""Rollback-owned adoption and frozen-control proof; no application certification."""
from datetime import date
import json
from unittest.mock import patch

from django.db import connection,transaction
from django.test import TestCase

from mta.serialization import digest
from mta.runtime.test_rationing_adoption import RationingAdoptionTests as AdoptionFixture
from mta.runtime.test_rationing_cut_guards import RationingCutGuardTests as Fixture
from mta.runtime.test_dated_history_storage import DatedHistoryStorageTests,row
from mta.runtime.dated_history_delta import FAMILIES,COMPLETE_REMARKS
from mta.runtime.dated_history_reader import read_cut,iter_occurrences,iter_image
from mta.runtime.dated_history_adoption import adopt
from mta.runtime.dated_history_writer import begin_initial_anchors,seal_initial_anchors,write_day
from mta.runtime.state_cut_models import OperationalStateCut
from mta.runtime.ingestion_models import IngestionRevisionState


class DatedHistoryLifecycleTests(TestCase):
    new_run=Fixture.new_run
    tearDown=Fixture.tearDown
    certify_metadata=AdoptionFixture.certify_metadata
    preserved=AdoptionFixture.preserved
    provisioner=AdoptionFixture.provisioner
    constraints=DatedHistoryStorageTests.constraints
    accept=DatedHistoryStorageTests.accept

    def setUp(self):
        AdoptionFixture.setUp(self)
        self.profile['delivery']['batch']={'DailyConsumptionHorizonDBM':1,'GatherSuspensionHistory':1}
        self.profile['complete_daily']={'policy':'generic-finalization-v1','consumption_days':1,'remark_days':30}
        self.opening={f:[row(f,'2026-07-09'),row(f,'2026-07-09'),row(f,'2026-07-10'),row(f,'2026-01-01')]
                      for f in FAMILIES}
        for section in ('dbm','bpr','orders','complete'):
            self.raw['opening']['state'][section]={f.rsplit('/',1)[1]:rr for f,rr in self.opening.items() if f.split('/')[1]==section}

    def initialize(self,*,anchors=False):
        from mta.runtime.input_storage import save_input
        from mta.runtime import opening_storage
        from mta.mdm.initialization import initialization_table
        self.owner.input_digest=digest(self.raw)
        self.owner.configuration_digest=digest(self.profile)
        self.owner.save(update_fields=['input_digest','configuration_digest'])
        self.owner.input_payload=save_input(self.owner,self.raw,version=3,
            image_writer=opening_storage.save_image,table_selector=initialization_table)
        cuts=begin_initial_anchors(self.owner,profile=self.profile) if anchors else {}
        self.owner.input_manifest_digest=digest(self.owner.input_payload)
        self.owner.receipt_digest='7'*64
        self.owner.save(update_fields=['input_payload','input_manifest_digest','receipt_digest'])
        seal_initial_anchors(cuts,self.owner)
        self.constraints()
        return cuts

    def legacy_day(self,values,*,predecessor=None,day=date(2026,7,10)):
        from mta.runtime.relational_state import save_image
        run=self.new_run(predecessor=predecessor,business_date=day)
        images={f:save_image(run,f,f,rows) for f,rows in values.items()}
        self.accept(run,images)
        return run,images

    def test_initial_anchors_and_frozen_first_own_successor(self):
        from mta.runtime.dated_history_audit import audit_image
        self.initialize(anchors=True)
        self.certify_metadata()
        run=self.new_run()
        first={}
        for f in FAMILIES:
            # All configured/90-day expiry rules remove the January fixture;
            # unbounded and postrule histories preserve that exact old fact.
            prior=self.opening[f] if f.endswith('/SpikeOrderClosureHistory') else self.opening[f][:2]+self.opening[f][3:]
            if f.endswith('/DailyConsumption'):prior=[]
            elif f.endswith(('/OrderDataSummary','/SuspendHistory')):prior=prior[:2]
            first[f]=self.opening[f][:3] if f in COMPLETE_REMARKS else prior+[row(f,'2026-07-10')]
        epoch=IngestionRevisionState.objects.get(pk=self.owner.pk).operational_epoch
        images={f:write_day(run,f,rr) for f,rr in first.items()}
        self.accept(run,images)
        self.assertGreater(IngestionRevisionState.objects.get(pk=self.owner.pk).operational_epoch,epoch)
        successor=self.new_run(predecessor=run,business_date=date(2026,7,11))
        next_rows={f:([] if f.endswith('/DailyConsumption') else rr)+([] if f in COMPLETE_REMARKS else [row(f,'2026-07-11')]) for f,rr in first.items()}
        newer={f:write_day(successor,f,rr) for f,rr in next_rows.items()}
        self.accept(successor,newer)
        for f in FAMILIES:
            self.assertEqual(list(iter_image(run,images[f])),first[f])
            self.assertEqual(list(iter_image(successor,newer[f])),next_rows[f])
            self.assertEqual(audit_image(successor,newer[f])['count'],len(next_rows[f]))

    def test_disabled_gathering_preserves_old_and_current_occurrences(self):
        self.profile['delivery']['batch']['GatherSuspensionHistory']=0
        self.initialize(anchors=True)
        run=self.new_run();f='closing/dbm/SuspendHistory'
        # Later in-memory control changes are not this persisted run's profile.
        self.profile['delivery']['batch']['GatherSuspensionHistory']=1
        expected=self.opening[f]
        with self.assertRaisesRegex(ValueError,'Disabled suspension gathering'):
            write_day(run,f,expected+[row(f,'2026-07-10')])
        item=write_day(run,f,expected)
        self.accept(run,{f:item})
        cut=read_cut(item['cut_id'])
        self.assertEqual((cut.body['inserted'],cut.body['removed']),(0,0))
        self.assertEqual(list(iter_image(run,item)),expected)

    def test_bpr_retention_uses_its_own_frozen_finalization_control(self):
        self.profile['complete_daily']['consumption_days']=30
        self.initialize(anchors=True)
        run=self.new_run()
        self.profile['complete_daily']['consumption_days']=1
        f='closing/bpr/DailyConsumption'
        expected=self.opening[f][:2]+[row(f,'2026-07-10')]
        item=write_day(run,f,expected)
        dbm='closing/dbm/DailyConsumption'
        dbm_item=write_day(run,dbm,[row(dbm,'2026-07-10')])
        self.accept(run,{f:item,dbm:dbm_item})
        self.assertEqual(list(iter_image(run,item)),expected)
        self.assertEqual(list(iter_image(run,dbm_item)),[row(dbm,'2026-07-10')])
        self.assertEqual(item['table'],'BPR/DailyConsumption')
        self.assertEqual(dbm_item['table'],'DBM/DailyConsumption')

    def test_bpr_without_finalization_retains_old_rows_and_replaces_only_today(self):
        del self.profile['complete_daily']
        self.initialize(anchors=True)
        run=self.new_run();f='closing/bpr/DailyConsumption'
        expected=self.opening[f][:2]+self.opening[f][3:]+[row(f,'2026-07-10')]
        item=write_day(run,f,expected)
        self.accept(run,{f:item})
        self.assertEqual(list(iter_image(run,item)),expected)

    def test_disabled_complete_families_stay_absent_across_initialization_and_adoption(self):
        del self.profile['complete_daily']
        anchors=self.initialize(anchors=True)
        self.certify_metadata()
        self.assertFalse(set(anchors)&COMPLETE_REMARKS)
        # Empty terminal population is not a substitute for an absent owner.
        run=self.new_run()
        for f in COMPLETE_REMARKS:
            with self.assertRaisesRegex(ValueError,'Disabled complete history'):
                write_day(run,f,[])
        images={}
        for f in FAMILIES:
            if f in COMPLETE_REMARKS:continue
            prior=self.opening[f] if f.endswith('/SpikeOrderClosureHistory') else self.opening[f][:2]+self.opening[f][3:]
            if f=='closing/dbm/DailyConsumption':prior=[]
            elif f.endswith(('/OrderDataSummary','/SuspendHistory')):prior=prior[:2]
            images[f]=write_day(run,f,prior+[row(f,'2026-07-10')])
        self.accept(run,images)
        before=self.preserved()
        with self.provisioner():
            receipts=adopt(self.owner);repeat=adopt(self.owner)
        for f in COMPLETE_REMARKS:
            self.assertEqual(receipts[f],{'status':'FINALIZATION_DISABLED'})
        self.assertEqual(receipts,repeat)
        self.assertEqual(self.preserved(),before)
        self.assertFalse(OperationalStateCut.objects.filter(family__in=COMPLETE_REMARKS).exists())

    def test_initial_anchor_profile_must_match_initialized_configuration(self):
        self.initialize()
        from copy import deepcopy
        altered=deepcopy(self.profile);altered['complete_daily']['remark_days']=1
        with self.assertRaisesRegex(ValueError,'profile differs'):
            begin_initial_anchors(self.owner,profile=altered)
        self.assertFalse(OperationalStateCut.objects.exists())

    def test_unowned_frozen_profile_and_missing_qualified_anchor_refuse(self):
        from copy import deepcopy
        self.initialize()
        run=self.new_run()
        f='closing/dbm/DailyConsumption'
        with self.assertRaisesRegex(ValueError,'requires its initialized or adopted predecessor'):
            write_day(run,f,[row(f,'2026-07-10')])
        self.assertFalse(OperationalStateCut.objects.exists())
        with transaction.atomic():
            def altered(raw):
                raw['profile']=deepcopy(raw['profile'])
                raw['profile']['delivery']['batch']['DailyConsumptionHorizonDBM']=90
            changed=self.new_run(raw_change=altered)
            with self.assertRaisesRegex(ValueError,'Historical initialization configuration differs'):
                write_day(changed,f,[row(f,'2026-07-10')])
            self.assertFalse(OperationalStateCut.objects.exists())
            transaction.set_rollback(True)

    def test_populated_adoption_preserves_all_old_rows_and_epochs(self):
        from mta.runtime.relational_state import load_image
        self.initialize()
        first,old1=self.legacy_day({f:[row(f,'2026-07-10')] for f in FAMILIES})
        values={f:[row(f,'2026-07-10'),row(f,'2026-07-11')]*2 for f in FAMILIES}
        last,old2=self.legacy_day(values,predecessor=first,day=date(2026,7,11))
        self.certify_metadata();before=self.preserved()
        with self.assertRaisesRegex(ValueError,'trusted provisioning session'):adopt(self.owner)
        with self.provisioner():
            receipts=adopt(self.owner);self.constraints();repeat=adopt(self.owner)
        self.assertEqual(self.preserved(),before)
        for f in FAMILIES:
            self.assertEqual(receipts[f]['status'],'ADOPTED')
            self.assertEqual(repeat[f]['status'],'EXISTING')
            self.assertEqual(repeat[f]['root_digest'],receipts[f]['root_digest'])
            self.assertEqual(load_image(first,old1[f]),[row(f,'2026-07-10')])
            self.assertEqual(load_image(last,old2[f]),values[f])
        next_run=self.new_run(predecessor=last,business_date=date(2026,7,12))
        images={f:write_day(next_run,f,([] if f.endswith('/DailyConsumption') else rr)+([] if f in COMPLETE_REMARKS else [row(f,'2026-07-12')]))
                for f,rr in values.items()}
        self.accept(next_run,images)
        self.assertEqual(self.preserved()[0][:2],before[0][:2])
        # Original run records remain byte exact even after the own successor.
        saved={json.loads(r[0])['id']:r for r in before[1]}
        now={json.loads(r[0])['id']:r for r in self.preserved()[1]}
        self.assertEqual({k:now[k] for k in saved},saved)

    def test_adoption_late_transport_failure_rolls_back_every_family(self):
        from mta.runtime import relational_state
        self.initialize();self.legacy_day({f:[row(f,'2026-07-10')] for f in FAMILIES})
        self.certify_metadata();before=self.preserved()
        original=relational_state.iter_image
        def faulty(run,item):
            for value in original(run,item):
                yield dict(value,SKUCode='fault') if item['image'].endswith('/SuspendHistory') else value
        with self.provisioner(),patch.object(relational_state,'iter_image',faulty):
            with self.assertRaisesRegex(ValueError,'source values/type/order/count'):adopt(self.owner)
        self.assertFalse(OperationalStateCut.objects.exists())
        self.assertEqual(self.preserved(),before)
        with self.provisioner():adopt(self.owner);self.constraints()

    def test_unused_opening_adopts_without_revision(self):
        self.initialize();self.certify_metadata();before=self.preserved()
        with self.provisioner():receipts=adopt(self.owner);self.constraints()
        self.assertEqual(self.preserved(),before)
        for f in FAMILIES:
            self.assertEqual(receipts[f]['status'],'ADOPTED')
            self.assertEqual([r for _,r in iter_occurrences(read_cut(receipts[f]['cut_id']))],self.opening[f])

    def test_unqualified_old_descriptor_retains_its_codec(self):
        f='closing/dbm/OrderData'
        self.initialize()
        last,_=self.legacy_day({f:[{'SKUCode':'subset'}]})
        self.certify_metadata();before=self.preserved()
        with self.provisioner():receipts=adopt(self.owner);self.constraints()
        self.assertEqual(receipts[f]['status'],'LEGACY_DESCRIPTOR_RETAINED')
        self.assertEqual(self.preserved(),before)
        run=self.new_run(predecessor=last,business_date=date(2026,7,11))
        self.assertIsNone(write_day(run,f,[{'SKUCode':'subset'}]))

    def test_active_or_ambiguous_prefix_refuses_without_anchors(self):
        self.initialize()
        with transaction.atomic():
            self.new_run()
            with self.provisioner(),self.assertRaisesRegex(ValueError,'unfinished calculation'):adopt(self.owner)
            transaction.set_rollback(True)
        self.legacy_day({f:[] for f in FAMILIES})
        self.legacy_day({f:[] for f in FAMILIES},day=date(2026,7,11))
        with self.provisioner(),self.assertRaisesRegex(ValueError,'one exact accepted terminal prefix'):adopt(self.owner)
        self.assertFalse(OperationalStateCut.objects.exists())
