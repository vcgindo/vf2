"""Scoped master handoff contracts; no native/transaction acceptance claim."""
from copy import deepcopy
from contextlib import ExitStack
from types import SimpleNamespace as NS
from unittest.mock import patch,MagicMock
import unittest

from mta.runtime import placement_master_publication as handoff
from mta.serialization import digest


class PlacementMasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os,django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY','local-unit-check-only')
        django.setup()

    def basis(self):
        from mta.application.persistent_master import CONTRACT
        capture=dict(initialization_id='init',base_revision_id='base',receipt_digest='capture',
                     configuration_digest='profile',qualified_master_reuse=True)
        producer=dict(contract=CONTRACT,qualified=True,reused=False,configuration_digest='profile',
                      full_master_producer_calls=1,changed_work=None)
        prefix=[NS(pk=name,digest=name+'-digest',snapshot=NS(manifest=dict(
            references={'profile':'profile'},metadata=dict(master_reused=False,
                master_work=None,master_outcome='APPLIED')))) for name in ('PRE_BPR','BPR','DBM')]
        return capture,producer,prefix

    def test_intake_reuse_flag_never_rewrites_actual_producer(self):
        capture,producer,prefix=self.basis()
        original=deepcopy(producer)
        for reuse in (False,True):
            capture['qualified_master_reuse']=reuse
            with patch.object(handoff,'_owner',return_value=(prefix,NS(pk='final'))), \
                 patch.object(handoff,'_static_roots',return_value={'MasterData':'root'}), \
                 patch.object(handoff,'_promotion',return_value=(None,{'parent_id':'DBM'})):
                result=handoff.publication_master('run',capture,producer,'state')
            self.assertEqual(producer,original)
            self.assertIs(result['reused'],False)
            self.assertIs(result[handoff.KEY]['capture_selected_reuse'],reuse)
            self.assertEqual(result[handoff.KEY]['master_promotion']['parent_id'],'DBM')

    def test_producer_false_claims_and_phase_disagreement_deny(self):
        capture,producer,prefix=self.basis()
        for changes in ({'reused':True},{'qualified':False},{'full_master_producer_calls':True},
                        {'full_master_producer_calls':0},{'changed_work':{}},{'configuration_digest':'foreign'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                handoff._producer(capture,{**producer,**changes},prefix)
        for key,value in (('master_reused',True),('master_work',{}),('master_outcome','SKIPPED')):
            wrong=deepcopy(prefix);wrong[1].snapshot.manifest['metadata'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):handoff._producer(capture,producer,wrong)

    def test_pair_projection_changes_only_existing_non_nms_wire_type(self):
        from mta.runtime import relational_state as typed,phase_state
        rows=[dict(SKUCode='duplicate',NonNMS=value) for value in (None,0,1,1)]
        before=deepcopy(rows)
        source=dict(table='Importer/SkuLocAttributeData')
        with patch.object(typed,'load_image',return_value=rows):
            meta=handoff._pair_metadata('run',source)
        expected=[dict(row,NonNMS=None if row['NonNMS'] is None else bool(row['NonNMS'])) for row in rows]
        self.assertEqual(meta['count'],4)
        self.assertEqual(meta['digest'],digest(expected))
        self.assertEqual(rows,before)
        self.assertEqual(meta['fields'],[['SKUCode','SKUCode','str'],['NonNMS','NonNMS','bool']])

    def test_configuration_transport_boundary_including_empty_and_copy(self):
        images={str(i):dict(table='DBM/DBMSettingsTbl',count=count,digest=str(i))
                for i,count in enumerate((0,1,499,500,1001))}
        images['nonconfig']=dict(table='Importer/MasterData',count=999,digest='ignored')
        run=NS(production_manifest={'images':images})
        self.assertEqual([v['statements'] for v in handoff.configuration_writes(run)],[0,1,499,1,1])
        for table,count in (('Other/Settings',1),('DBM/DBMSettingsTbl',True),('DBM/DBMSettingsTbl',-1)):
            with self.subTest(table=table,count=count),self.assertRaises(ValueError):
                handoff.configuration_writes(NS(production_manifest={'images':{'bad':dict(table=table,count=count,digest='x')}}))

    def test_parent_receipt_and_phase_ancestry_are_required(self):
        from mta.runtime import master_revisions
        from mta.runtime.ingestion_models import MasterInputRevision
        from mta.runtime.ingestion_admission import receipt,REVISION_FIELDS
        capture,_,prefix=self.basis();run=NS(pk='run')
        def revision(pk,parent,phase,cut):
            value=dict(id=pk,initialization_id='init',parent_id=parent.pk if parent else None,
                run_id='run' if phase else 'prior',master_epoch=7,configuration_epoch=cut,
                partitions={} if phase is None else dict(contract=master_revisions.PHASE_CONTRACT,
                    phase_id=phase.pk,phase_digest=phase.digest))
            return NS(**value,pk=pk,parent=parent,status='ACCEPTED',receipt_digest=receipt(value))
        base=revision('base',None,None,10);parent=base
        for index,phase in enumerate(prefix):parent=revision(phase.pk,parent,phase,index+11)
        prefix[-1].metadata={'revision_after':[7,13,0,0,0]}
        with patch.object(MasterInputRevision.objects,'get',return_value=parent), \
             patch.object(master_revisions,'_validate_phase',return_value=run):
            self.assertIs(handoff._parent(run,capture,prefix),parent)
            parent.parent.receipt_digest='wrong'
            with self.assertRaisesRegex(ValueError,'ancestor receipt'):handoff._parent(run,capture,prefix)
            parent.parent.receipt_digest=receipt({k:getattr(parent.parent,k) for k in REVISION_FIELDS})
            parent.parent.parent=base
            parent.parent.parent_id=base.pk
            parent.parent.run_id='foreign'
            parent.parent.receipt_digest=receipt({k:getattr(parent.parent,k) for k in REVISION_FIELDS})
            with self.assertRaisesRegex(ValueError,'phase ancestry'):handoff._parent(run,capture,prefix)

    def test_promotion_uses_exact_write_delta_and_rejects_occupied_cut(self):
        from mta.runtime.ingestion_models import MasterInputRevision
        capture,_,prefix=self.basis();parent=NS(pk='DBM',master_epoch=7,configuration_epoch=31,receipt_digest='parent')
        state=NS(pk='init',master_epoch=7,configuration_epoch=34)
        with patch.object(handoff,'_parent',return_value=parent), \
             patch.object(handoff,'configuration_writes',return_value=[{'statements':2},{'statements':1}]), \
             patch.object(handoff,'connection',NS(in_atomic_block=True)), \
             patch.object(MasterInputRevision.objects,'filter') as occupied:
            occupied.return_value.exists.return_value=False
            owner,promotion=handoff._promotion('run',capture,prefix,state)
            self.assertIs(owner,parent);self.assertEqual(promotion['after'],[7,34])
            self.assertEqual(promotion['additional_master_increment'],0)
            state.configuration_epoch=35
            with self.assertRaisesRegex(ValueError,'configuration cut'):handoff._promotion('run',capture,prefix,state)
            state.configuration_epoch=34;occupied.return_value.exists.return_value=True
            with self.assertRaisesRegex(ValueError,'occupied'):handoff._promotion('run',capture,prefix,state)

    def test_matching_flag_dispatches_scoped_handoff_and_old_full_keeps_guard(self):
        from mta.runtime import capture_preparation
        from mta.runtime.ingestion_models import MasterInputRevision,IngestionRevisionState
        capture,producer,_=self.basis();capture['qualified_master_reuse']=False
        run=NS(production_manifest={});state=NS(master_epoch=7,configuration_epoch=34)
        with patch.object(MasterInputRevision.objects,'get',return_value=NS(run_id='prior')), \
             patch.object(IngestionRevisionState.objects,'select_for_update') as states, \
             patch.object(handoff,'publication_master',return_value={**producer,handoff.KEY:{}}) as adapter:
            states.return_value.get.return_value=state
            capture_preparation.publication_metadata(run,capture,producer,_scoped_placement=True)
            adapter.assert_called_once_with(run,capture,producer,state)
            self.assertEqual(run.production_manifest['master_preparation']['master_cut'],[7,34])
        self.assertEqual(capture['qualified_master_reuse'],False)

    def test_terminal_acceptance_revalidates_provenance(self):
        capture,producer,prefix=self.basis()
        expected={**producer,handoff.KEY:{'schema':handoff.PROVENANCE}}
        run=NS(production_manifest=dict(ingestion_preparation=capture,
            master_preparation={**expected,'master_cut':[7,34]}))
        state=NS(master_epoch=7,configuration_epoch=34)
        with patch.object(handoff,'publication_master',return_value=expected), \
             patch.object(handoff,'_owner',return_value=(prefix,None)), \
             patch.object(handoff,'_parent',return_value='accepted-DBM'), \
             patch('mta.runtime.receipt_integrity.verify_root') as verify:
            self.assertEqual(handoff.terminal_master_parent(run,'init','base',state),'accepted-DBM')
            verify.assert_called_once_with(run)
            run.production_manifest['master_preparation'][handoff.KEY]={'schema':'forged'}
            with self.assertRaisesRegex(ValueError,'provenance'):
                handoff.terminal_master_parent(run,'init','base',state)
