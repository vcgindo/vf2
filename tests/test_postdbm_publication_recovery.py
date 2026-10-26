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
