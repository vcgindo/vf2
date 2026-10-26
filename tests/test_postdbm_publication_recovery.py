"""Focused publication/compatibility checks; native proof remains independent."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch


class PostDbmPublicationRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY','local-unit-check-only')
        import django
        django.setup()

    def test_complete_histories_are_published_verbatim_without_collecting_or_reading_parent_rows(self):
        from mta.presentation import production_reports as reports
        from mta.application import production_output_policy
        for expanded in (False,True):
            with self.subTest(expanded=expanded),ExitStack() as stack:
                stack.enter_context(patch.object(reports.transaction,'get_autocommit',return_value=False))
                save=stack.enter_context(patch.object(reports.typed,'save',return_value={}))
                read=stack.enter_context(patch.object(reports.typed,'read'))
                collectors=[stack.enter_context(patch.object(owner,name)) for owner,name in (
                    (reports.operational_bor,'collect_bor_order_allocation_history'),
                    (reports.operational_bor,'collect_rrr_order_allocation_history'),
                    (reports.production_output_policy,'bor_oa_history'))]
                names=['BORWithOrderAllocation','RRR_OrderAllocation','AllocatedOrders','BOROARequirement',
                       'BOR_OrderAllocationHistory','RRR_OrderAllocationHistory']
                if expanded:names.append('SupplierDispatchReq')
                rows=[{'field':None,'quantity':0},{'field':'X','quantity':2},{'field':None,'quantity':0}]
                values={name:deepcopy(rows) for name in names};before=deepcopy(values)
                opening=dict(supplier={},production_report_policy={'bor_history_horizon':90,'rrr_history_horizon':90})
                if expanded:opening['production_report_schema']=production_output_policy.SOURCE_SCHEMA
                run=SimpleNamespace(kind='DAILY_CHAIN',status='RUNNING',input_digest='a'*64,
                    business_date=date(2026,10,25),predecessor_id='parent',predecessor=SimpleNamespace(output_digest='b'*64))
                images=reports._write_report_rows(run,values,opening)
                self.assertEqual(values,before)
                self.assertEqual(set(images),{reports.typed.PATHS[n] for n in names})
                self.assertEqual(save.call_count,len(names))
                for call in save.call_args_list:
                    self.assertIs(call.args[2],values[call.args[1]])
                    self.assertEqual(call.kwargs,{'expanded':expanded})
                read.assert_not_called()
                for collect in collectors:collect.assert_not_called()
                with patch.object(reports.transaction,'get_autocommit',return_value=True):
                    with self.assertRaisesRegex(ValueError,'running day transaction'):
                        reports._write_report_rows(run,values,opening)

    def test_incomplete_or_extra_history_roster_is_denied_and_current_only_keeps_original_owner(self):
        from mta.presentation import production_reports as reports
        current={name:[] for name in ('BORWithOrderAllocation','RRR_OrderAllocation','AllocatedOrders','BOROARequirement')}
        with patch.object(reports,'_write_sources') as ordinary,patch.object(reports,'_save_populations') as save:
            reports._write_report_rows('run',current,{})
            self.assertEqual(ordinary.call_args.args[2](),current)
            for extra in ({'BOR_OrderAllocationHistory':[]},{'RRR_OrderAllocationHistory':[]},
                          {'BOR_OrderAllocationHistory':[],'RRR_OrderAllocationHistory':[],'extra':[]}):
                with self.assertRaisesRegex(ValueError,'roster differs'):
                    reports._write_report_rows('run',dict(current,**extra),{})
            save.assert_not_called()

    def test_receipt_reader_retains_exact_old_recipe_without_weakening_identity(self):
        from mta.presentation import daily_sources as sources
        from mta.serialization import digest
        run=SimpleNamespace(input_digest='a'*64)
        receipt=SimpleNamespace(input_digest=run.input_digest,recipe_digest=sources.RETAINED_V6_RECIPE,
                                images={},images_digest=digest({}))
        with patch.object(sources.DailySourceReceipt.objects,'get',return_value=receipt):
            self.assertIs(sources.receipt(run),receipt)
            receipt.recipe_digest='unknown'
            with self.assertRaisesRegex(ValueError,'identity drift'):sources.receipt(run)
            receipt.recipe_digest=sources.RETAINED_V6_RECIPE;receipt.images_digest='wrong'
            with self.assertRaisesRegex(ValueError,'identity drift'):sources.receipt(run)
            receipt.images_digest=digest({});receipt.input_digest='wrong'
            with self.assertRaisesRegex(ValueError,'identity drift'):sources.receipt(run)
            receipt.input_digest=run.input_digest;receipt.recipe_digest=sources.RETAINED_V5_RECIPE
            receipt.images={'history':{'table':'bpr_history/old'}};receipt.images_digest=digest(receipt.images)
            with self.assertRaisesRegex(ValueError,'cannot own late BPR history'):sources.receipt(run)

    def request_value(self):
        from mta.runtime import production_post_dbm as entry,scoped_postdbm_recovery as recovery
        run=SimpleNamespace(pk=entry.AUTHORITY['run'],input_digest=entry.AUTHORITY['input_digest'],
                            input_manifest_digest=entry.AUTHORITY['input_manifest_digest'])
        with patch('release.native_identity.require_current',return_value=recovery.PREVIOUS):
            value=entry.request(run,expected_dbm_digest=entry.AUTHORITY['dbm_digest'],
                expected_action_revision=177,command_key=recovery.COMMAND)
        self.assertEqual(value['compatibility_digest'],recovery.COMPATIBILITY)
        return run,value

    def test_original_request_reconstruction_denies_any_request_or_phase_change(self):
        from mta.runtime import scoped_postdbm_recovery as recovery
        from mta.runtime.phase_state import recipe_digest
        run,value=self.request_value()
        self.assertEqual(recovery.frozen_request(value,recipe_digest()),value)
        for field in ('run_id','input_digest','input_manifest_digest','command_key','dbm_digest','action_revision','authority','dispositions'):
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'frozen request'):
                recovery.frozen_request(dict(value,**{field:'changed'}),recipe_digest())
        with self.assertRaisesRegex(ValueError,'phase recipe'):
            recovery.frozen_request(value,'changed')

    def test_source_guard_denies_extra_missing_and_changed_protected_sources(self):
        from mta.runtime import scoped_postdbm_recovery as recovery
        from mta.serialization import digest
        files={name:'a'*64 for name in recovery.ENTRY_FILES}
        protected={'engine.py':'b'*64,'migrations/001.py':'c'*64};files.update(protected)
        with patch.object(recovery,'PROTECTED',digest(protected)):
            recovery.unchanged_sources(files)
            for changed in (dict(files,**{'engine.py':'new'}),dict(files,**{'extra.py':'new'}),
                            {k:v for k,v in files.items() if k!='migrations/001.py'},
                            {k:v for k,v in files.items() if k not in recovery.ENTRY_FILES}):
                with self.assertRaisesRegex(ValueError,'other native source'):recovery.unchanged_sources(changed)

    def test_recovery_fence_and_completed_retry_require_exact_failed_ancestry(self):
        from mta.runtime import scoped_postdbm_recovery as recovery
        run,value=self.request_value();run.scope_attempts=MagicMock()
        failed=SimpleNamespace(pk=recovery.FAILED,run_id=run.pk,scope='PostDBM',status='FAILED',
            failure={'type':'ValueError','message':'Captured production report population roster differs'},
            command_key=recovery.COMMAND,compatibility_digest=recovery.COMPATIBILITY,
            expected_phase='DBM',expected_receipt_digest=value['dbm_digest'],action_revision=177,
            input_digest=value['input_digest'],input_manifest_digest=value['input_manifest_digest'],attempt_no=2)
        child=SimpleNamespace(**dict(vars(failed),pk='child',recovery_of=failed,attempt_no=3,status='ACTIVE'))
        with patch('mta.runtime.models.RunScopeAttempt.objects.get',return_value=failed):
            for latest in (failed,child):
                run.scope_attempts.order_by.return_value.first.return_value=latest
                for status in ('ACTIVE','FAILED','RELEASED'):
                    child.status=status
                    recovery.require_chain(run,value)
            for field,bad in (('command_key','other'),('action_revision',178),('compatibility_digest','other'),
                              ('run_id','other'),('expected_receipt_digest','other'),('attempt_no',7)):
                prior=getattr(child,field);setattr(child,field,bad)
                with self.subTest(field=field),self.assertRaises(ValueError):recovery.require_chain(run,value)
                setattr(child,field,prior)
            child.recovery_of=None
            with self.assertRaisesRegex(ValueError,'ancestry'):recovery.require_chain(run,value)

    def test_resolver_denies_schema_guard_certificate_and_release_authority_drift(self):
        from mta.runtime import scoped_postdbm_recovery as recovery,ingestion_authority as authority
        from mta.runtime.phase_state import recipe_digest
        run,value=self.request_value()
        old={k:'same' for k in authority.FIELDS}
        old.update(target_commit=recovery.PREVIOUS['source_commit'],target_release=recovery.PREVIOUS['manifest_sha256'])
        new=dict(old,target_commit='new',target_release='new')
        current=dict(recovery.PREVIOUS,source_commit='new',manifest_sha256='new')
        schema=({'certificate':'same'},None,recovery.SCHEMA,recovery.GUARD,None)
        with ExitStack() as stack:
            stack.enter_context(patch.object(recovery.Path,'read_bytes',return_value=b'{"files":{}}'))
            stack.enter_context(patch.object(recovery,'unchanged_sources'))
            stack.enter_context(patch.object(recovery,'require_chain'))
            stack.enter_context(patch.object(recovery.connection,'cursor'))
            stack.enter_context(patch('mta.runtime.input_reader.read_input',return_value={
                'initialization_binding':{'id':recovery.INITIALIZATION}}))
            admit=stack.enter_context(patch('mta.runtime.ingestion_admission._admit'))
            stack.enter_context(patch.object(authority,'read',side_effect=lambda c,i,r:old if r==old['target_release'] else new))
            extension=stack.enter_context(patch.object(authority,'read_schema_transition',return_value={
                'contract':authority.CODE_SCHEMA_CONTRACT}))
            effective=stack.enter_context(patch('mta.runtime.ingestion_admission.effective_schema',return_value=schema))
            self.assertEqual(recovery.resolve(run,value,current,recipe_digest()),value)
            self.assertEqual(admit.call_count,2)
            for index,changed in ((0,{'certificate':'changed'}),(2,'changed-schema'),(3,'changed-guard')):
                revised=list(schema);revised[index]=changed
                effective.side_effect=[schema,tuple(revised)]
                with self.subTest(index=index),self.assertRaisesRegex(ValueError,'code-only authority'):
                    recovery.resolve(run,value,current,recipe_digest())
            effective.side_effect=None
            new['certification_digest']='changed'
            with self.assertRaisesRegex(ValueError,'code-only authority'):recovery.resolve(run,value,current,recipe_digest())
            new['certification_digest']=old['certification_digest']
            extension.return_value=None
            with self.assertRaisesRegex(ValueError,'code-only authority'):recovery.resolve(run,value,current,recipe_digest())

    def test_final_source_gate_denies_changed_accepted_history_values_and_roster(self):
        from mta.application.stage_calculation_sources import CalculationSources
        from mta.runtime import scoped_final
        from mta.serialization import digest
        rows=[{'x':None},{'x':2},{'x':None}]
        consumers=dict(pick_bands={},routes={},operational={},production_reports={
            'BOR_OrderAllocationHistory':{'image':'history'}})
        manifest=dict(metadata={'calculation_digest':'a'*64},consumers=consumers,
                      images={'history':{'count':3,'digest':digest(rows)}})
        sources=CalculationSources(calculation_digest='a'*64,pick_bands={},routes={},operational={},
                                   production_reports={'BOR_OrderAllocationHistory':deepcopy(rows)})
        phase=SimpleNamespace(snapshot=SimpleNamespace(manifest=manifest))
        with ExitStack() as stack:
            stack.enter_context(patch.object(scoped_final,'require_pending_final'))
            receipt=SimpleNamespace(pk='receipt',revision_before='revision')
            stack.enter_context(patch('mta.runtime.models.RunPhaseAcceptance.objects.get',return_value=receipt))
            for name in ('verify_write','next_cut','identity'):stack.enter_context(patch.object(scoped_final.scope_revisions,name))
            stack.enter_context(patch.object(scoped_final,'accepted_prefix',return_value=([phase],None)))
            scoped_final.require_final_sources('run',receipt,sources)
            sources.production_reports['BOR_OrderAllocationHistory'][0]['x']=0
            with self.assertRaisesRegex(ValueError,'finite consumers differ'):
                scoped_final.require_final_sources('run',receipt,sources)
            sources.production_reports['BOR_OrderAllocationHistory']=deepcopy(rows)
            sources.production_reports['extra']=[]
            with self.assertRaisesRegex(ValueError,'finite consumers differ'):
                scoped_final.require_final_sources('run',receipt,sources)

    def publication_harness(self):
        from mta.runtime import scoped_postdbm_recovery as recovery,production_post_dbm as entry
        from mta.runtime.master_revisions import STATIC_TABLES
        from mta.application.persistent_master import CONTRACT
        run,value=self.request_value()
        capture=dict(receipt_digest='067ffb189928dbd9bf7f54394ee5263038a7b7411dbfbdea1969c7dec2806c7d',
                     qualified_master_reuse=True)
        producer=dict(contract=CONTRACT,qualified=True,reused=False,configuration_digest=entry.AUTHORITY['profile_digest'],
                      full_master_producer_calls=1,changed_work=None)
        images={name:dict(count=3,digest='d'*64,fields=[['x','x','str']]) for name in STATIC_TABLES}
        manifest=dict(metadata=dict(master_reused=False,master_work=None,master_outcome='APPLIED'),
            references={'profile':entry.AUTHORITY['profile_digest']},images=images,
            state={'importer':{name:{'image':name} for name in STATIC_TABLES}})
        pre=SimpleNamespace(pk='pre',digest='64657436bc1b291ce93a62427b8593d95d4b7b88722333a3476f597eeb544452',
                            snapshot=SimpleNamespace(manifest=deepcopy(manifest)))
        dbm=SimpleNamespace(pk=entry.AUTHORITY['dbm'],digest=entry.AUTHORITY['dbm_digest'],
                            snapshot=SimpleNamespace(manifest=deepcopy(manifest)))
        run.production_manifest={'images':{'closing/importer/'+name:deepcopy(image) for name,image in images.items()}}
        attempt=SimpleNamespace(status='ACTIVE',scope='PostDBM',command_key=recovery.COMMAND,
            compatibility_digest=recovery.COMPATIBILITY,action_revision=177,expected_phase='DBM',
            expected_receipt_digest=entry.AUTHORITY['dbm_digest'])
        stack=ExitStack();self.addCleanup(stack.close)
        pending=stack.enter_context(patch('mta.runtime.scoped_final.require_pending_final'))
        stack.enter_context(patch('mta.runtime.scoped_final.accepted_prefix',return_value=([pre,dbm],None)))
        stack.enter_context(patch('mta.runtime.scope_revisions.identity',return_value=capture))
        stack.enter_context(patch('mta.runtime.models.RunPhaseAcceptance.objects'))\
            .select_related.return_value.get.return_value=SimpleNamespace(attempt=attempt)
        stack.enter_context(patch.object(recovery.connection,'cursor'))
        stack.enter_context(patch.object(recovery,'terminal_pair_metadata',side_effect=lambda run,source:source))
        return recovery,run,capture,producer,pre,dbm,attempt,pending

    def test_terminal_pair_projection_preserves_null_and_uses_existing_boolean_wire_type(self):
        from mta.runtime import scoped_postdbm_recovery as recovery
        from mta.serialization import digest
        rows=[{'NonNMS':None},{'NonNMS':0},{'NonNMS':1},{'NonNMS':0}]
        before=deepcopy(rows)
        with patch('mta.runtime.relational_state.load_image',return_value=rows):
            result=recovery.terminal_pair_metadata('run',{'table':'Importer/SkuLocAttributeData'})
        self.assertEqual(rows,before)
        self.assertEqual(result['digest'],digest([{'NonNMS':None},{'NonNMS':False},{'NonNMS':True},{'NonNMS':False}]))
        self.assertEqual(result['fields'],[['NonNMS','NonNMS','bool']])

    def test_terminal_provenance_retains_capture_and_truthful_execution(self):
        recovery,run,capture,producer,pre,dbm,attempt,pending=self.publication_harness()
        before=deepcopy(capture);original=deepcopy(producer)
        result=recovery.publication_master(run,capture,producer)
        self.assertEqual(capture,before);self.assertEqual(producer,original)
        self.assertIs(result['reused'],False);self.assertIs(result['qualified'],True)
        provenance=result['scoped_execution_provenance']
        self.assertTrue(provenance['capture_selected_reuse'])
        self.assertFalse(provenance['accepted_master_reused'])
        self.assertEqual(provenance['accepted_phases'][-1]['digest'],dbm.digest)
        pending.assert_called_once_with(run)

    def test_terminal_provenance_denies_wrong_pending_owner_and_accepted_execution(self):
        recovery,run,capture,producer,pre,dbm,attempt,pending=self.publication_harness()
        for field,changed in (('scope','Full'),('status','RELEASED'),('command_key','new'),
                              ('compatibility_digest','new'),('action_revision',178)):
            old=getattr(attempt,field);setattr(attempt,field,changed)
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'publication owner'):
                recovery.publication_master(run,capture,producer)
            setattr(attempt,field,old)
        pre.snapshot.manifest['metadata']['master_reused']=True
        with self.assertRaisesRegex(ValueError,'accepted execution'):recovery.publication_master(run,capture,producer)
        pre.snapshot.manifest['metadata']['master_reused']=False
        pending.side_effect=ValueError('no pending DAY_FINAL')
        with self.assertRaisesRegex(ValueError,'pending DAY_FINAL'):recovery.publication_master(run,capture,producer)

    def test_terminal_provenance_denies_relabelled_capture_producer_or_static_population(self):
        recovery,run,capture,producer,pre,dbm,attempt,pending=self.publication_harness()
        for field,changed in (('reused',True),('qualified',False),('full_master_producer_calls',0),
                              ('full_master_producer_calls',True),('configuration_digest','other'),('changed_work',{})):
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'execution provenance'):
                recovery.publication_master(run,capture,dict(producer,**{field:changed}))
        with self.assertRaisesRegex(ValueError,'execution provenance'):
            recovery.publication_master(run,dict(capture,qualified_master_reuse=False),producer)
        run.production_manifest['images']['closing/importer/MasterData']['digest']='changed'
        with self.assertRaisesRegex(ValueError,'population differs'):recovery.publication_master(run,capture,producer)

    def test_ordinary_full_master_publication_keeps_strict_reuse_validation(self):
        from mta.runtime.capture_preparation import publication_metadata
        run=SimpleNamespace(pk='ordinary-full',production_manifest={})
        capture=dict(base_revision_id='base',initialization_id='owner',configuration_digest='a'*64,
                     qualified_master_reuse=False)
        producer=dict(configuration_digest='a'*64,reused=False,qualified=True)
        with patch('mta.runtime.ingestion_models.MasterInputRevision.objects') as bases, \
                patch('mta.runtime.ingestion_models.IngestionRevisionState.objects') as states, \
                patch('mta.runtime.scoped_postdbm_recovery.publication_master') as bounded:
            bases.get.return_value=SimpleNamespace(run_id='parent')
            states.select_for_update.return_value.get.return_value=SimpleNamespace(master_epoch=4,configuration_epoch=5)
            publication_metadata(run,capture,producer)
            self.assertEqual(run.production_manifest['master_preparation'],dict(producer,master_cut=[4,5]))
            self.assertIs(run.production_manifest['ingestion_preparation'],capture)
            with self.assertRaisesRegex(ValueError,'Native prepared producer result differs'):
                publication_metadata(run,dict(capture,qualified_master_reuse=True),producer)
            bounded.assert_not_called()

    def test_terminal_master_binds_exact_publication_cut_without_counter_write(self):
        from mta.runtime import scoped_postdbm_recovery as recovery
        parent=SimpleNamespace(pk='parent',receipt_digest='a'*64)
        state=SimpleNamespace(pk=recovery.INITIALIZATION,master_epoch=41,configuration_epoch=402)
        capture={'base_revision_id':'base'};producer={'scoped_execution_provenance':{'preserved':True}}
        with patch.object(recovery,'_pending_owner'),patch.object(recovery,'_master_parent',return_value=parent), \
                patch.object(recovery,'publication_configuration_writes',return_value=['verified-images']), \
                patch.object(recovery.connection,'in_atomic_block',True), \
                patch('mta.runtime.ingestion_models.IngestionRevisionState.objects') as states, \
                patch('mta.runtime.ingestion_models.MasterInputRevision.objects') as revisions:
            revisions.filter.return_value.exists.return_value=False
            result=recovery.promote_master('run',capture,producer,state)
            self.assertEqual(state.master_epoch,41)
            self.assertEqual(result['scoped_execution_provenance']['master_promotion']['after'],[41,402])
            self.assertEqual(result['scoped_execution_provenance']['master_promotion']['additional_master_increment'],0)
            self.assertEqual(producer,{'scoped_execution_provenance':{'preserved':True}})
            for changed in ([41,312],[41,403],[42,402]):
                state.master_epoch,state.configuration_epoch=changed
                with self.assertRaisesRegex(ValueError,'promotion cut differs'):
                    recovery.promote_master('run',capture,producer,state)
            state.master_epoch,state.configuration_epoch=41,402
            revisions.filter.return_value.exists.return_value=True
            with self.assertRaisesRegex(ValueError,'already occupied'):
                recovery.promote_master('run',capture,producer,state)
            states.assert_not_called()

    def test_terminal_configuration_plan_counts_repeated_images_and_rejects_changed_transport(self):
        from mta.runtime import scoped_postdbm_recovery as recovery
        images={str(i):dict(table='BPR/UI_ReportConfigurations',count=9,digest='a'*64) for i in range(10)}
        run=SimpleNamespace(production_manifest={'images':images})
        result=recovery.publication_configuration_writes(run)
        self.assertEqual(len(result),10);self.assertEqual(sum(i['count'] for i in result),90)
        images['0']['count']=500
        with self.assertRaisesRegex(ValueError,'transport differs'):recovery.publication_configuration_writes(run)
        images['0']['count']=8
        with self.assertRaisesRegex(ValueError,'write plan differs'):recovery.publication_configuration_writes(run)

    def test_terminal_master_acceptance_rechecks_promoted_cut_and_parent(self):
        from mta.runtime import scoped_postdbm_recovery as recovery
        parent=SimpleNamespace(pk='parent',receipt_digest='a'*64)
        state=SimpleNamespace(pk=recovery.INITIALIZATION,master_epoch=41,configuration_epoch=402)
        promotion=dict(parent_id='parent',captured_base_id='base',before=[41,312],after=[41,402],parent_receipt='a'*64,
                       configuration_writes=['verified-images'],additional_master_increment=0)
        run=SimpleNamespace(production_manifest=dict(master_preparation=dict(master_cut=[41,402],
            scoped_execution_provenance={'master_promotion':promotion}),ingestion_preparation={'base_revision_id':'base'}))
        with patch.object(recovery,'_pending_owner'),patch.object(recovery,'_master_parent',return_value=parent), \
                patch.object(recovery,'publication_configuration_writes',return_value=['verified-images']), \
                patch('mta.runtime.receipt_integrity.verify_root') as verify:
            self.assertIs(recovery.terminal_master_parent(run,recovery.INITIALIZATION,'base',state),parent)
            verify.assert_called_once_with(run)
            for changed in ([41,312],[42,402]):
                state.master_epoch,state.configuration_epoch=changed
                with self.assertRaisesRegex(ValueError,'acceptance promotion differs'):
                    recovery.terminal_master_parent(run,recovery.INITIALIZATION,'base',state)
            state.master_epoch,state.configuration_epoch=41,402
            promotion['parent_id']='foreign'
            with self.assertRaisesRegex(ValueError,'acceptance promotion differs'):
                recovery.terminal_master_parent(run,recovery.INITIALIZATION,'base',state)

    def test_terminal_remarks_keep_exact_prefix_when_live_owner_advances(self):
        from mta.presentation import terminal_scoped_remarks as terminal,scoped_remarks
        from mta.serialization import digest
        locator=dict(live_highwater=2,capture_id=9,watermark=0,provenance_digest='a'*64)
        fresh=scoped_remarks.RemarkBinding('run',9,0,3,None,0,'b'*64,dict(locator,live_highwater=3))
        rows=[{'Remark':None,'SKUCode':'A'},{'Remark':'same','SKUCode':'A'}]
        with patch.object(terminal,'ROWS_DIGEST',digest(rows)), \
                patch.object(scoped_remarks.RemarkBinding,'verify_rows') as verify, \
                patch.object(scoped_remarks.RemarkBinding,'rows',return_value=rows):
            bound,actual=terminal.retained_prefix(fresh,locator)
            self.assertEqual(actual,rows);self.assertEqual(bound.highwater,2);self.assertEqual(fresh.highwater,3)
            self.assertEqual(bound.provenance(),locator);verify.assert_called_once()
            with self.assertRaisesRegex(ValueError,'prefix_differs'):
                terminal.retained_prefix(fresh,dict(locator,provenance_digest='changed'))
            with self.assertRaisesRegex(ValueError,'prefix_differs'):
                terminal.retained_prefix(fresh,dict(locator,live_highwater=1))
            rows[0]['Remark']='altered'
            with self.assertRaisesRegex(ValueError,'rows_differ'):terminal.retained_prefix(fresh,locator)

    def test_terminal_remark_rows_and_parent_sql_use_same_source_descriptor(self):
        from mta.presentation import terminal_scoped_remarks as terminal,daily_sources,selective
        item={'table':terminal.TABLE};rows=[{'Remark':'one'},{'Remark':'two'}]
        bound=SimpleNamespace(query=lambda:('PREFIX_SQL',['bound-cut']))
        with patch.object(terminal,'binding',return_value=(bound,rows,item)), \
                patch.object(daily_sources,'image_metadata',return_value=item), \
                patch.object(selective,'image_metadata',return_value=item), \
                patch('mta.presentation.ancillary_live.image_query') as original:
            self.assertEqual(daily_sources.image_rows('run','path'),rows)
            self.assertEqual(selective.image_query('run','path'),('PREFIX_SQL',['bound-cut']))
            original.assert_not_called()
            with self.assertRaisesRegex(ValueError,'publication_differs'):
                terminal.read('run',dict(item,digest='changed'))

    def test_terminal_remark_publisher_rejects_moved_cut_and_leaves_other_runs_alone(self):
        from mta.presentation import terminal_scoped_remarks as terminal
        from mta.runtime.production_post_dbm import AUTHORITY
        with patch('mta.runtime.scoped_postdbm_recovery._pending_owner') as pending, \
                patch('mta.runtime.models.RemarkOwner.objects') as owners, \
                patch.object(terminal,'binding') as bind:
            self.assertEqual(terminal.publish(SimpleNamespace(pk='other')),{});pending.assert_not_called()
            owners.select_for_update.return_value.get.return_value=SimpleNamespace(next_ordinal=3)
            with self.assertRaisesRegex(ValueError,'publication_cut_changed'):
                terminal.publish(SimpleNamespace(pk=AUTHORITY['run']))
            bind.assert_not_called()
