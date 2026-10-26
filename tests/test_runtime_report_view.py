"""Finite recipe compatibility and request/receipt ownership, without DB claims."""
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch,MagicMock

from mta.serialization import digest
from mta.presentation import runtime_report_view as module
from mta.presentation.context import PublicationUnavailable


class RuntimeReportViewTests(unittest.TestCase):
    def test_real_59ca_recipes_and_unchanged_dependencies_remain_exact(self):
        from mta.presentation import scoped_view, scoped_selection
        self.assertEqual(scoped_view.recipe_digest(),
            'c0cb3006571037d08bbee122ffc2db414363347cc5d6d63932bb060d468a97bd')
        self.assertEqual(scoped_selection.recipe_digest(),
            '885c44e7e2c5c4788eaa861d5e41785b6e5ba619f69017f6f3f20a958146adad')
        self.assertNotEqual(module.recipe_digest(), scoped_view.recipe_digest())
        self.assertNotEqual(scoped_selection.publication_recipe_digest(),scoped_selection.recipe_digest())

    def test_changed_reader_cannot_keep_legacy_recipe(self):
        from mta.presentation import legacy_scope_read_compatibility as profile
        with patch.object(profile.inspect,'getsource',return_value='changed reader'):
            with self.assertRaisesRegex(PublicationUnavailable,'legacy_scope_read_profile_source_differs'):
                module.legacy_view_recipe()
            with self.assertRaises(PublicationUnavailable):module.legacy_selection_recipe()

    def test_startup_recipe_uses_authenticated_request_schema_without_adopting_new_config(self):
        from mta.presentation import scoped_selection
        from mta.runtime.production_scope import PUBLICATION_SCHEMA
        run=NS(pk='owned')
        with patch('mta.runtime.input_reader.read_input',return_value={'scope_request':{'schema':'old'}}), \
                patch.object(module,'configuration') as checked:
            self.assertEqual(scoped_selection.recipe_for_run(run),module.LEGACY_SELECTION_RECIPE)
            checked.assert_not_called()
        with patch('mta.runtime.input_reader.read_input',return_value={'scope_request':{'schema':PUBLICATION_SCHEMA}}), \
                patch.object(module,'configuration',side_effect=PublicationUnavailable('invalid configuration')):
            with self.assertRaises(PublicationUnavailable):scoped_selection.recipe_for_run(run)

    def test_new_configuration_requires_exact_captured_request_and_hook(self):
        from mta.runtime.production_scope import PUBLICATION_SCHEMA
        from mta.runtime.scope_runtime_reports import PUBLICATION_REFERENCE
        config=dict(schema=PUBLICATION_REFERENCE,configuration_digest='b'*64)
        hook=dict(site_code='TEST')
        request=dict(schema=PUBLICATION_SCHEMA,scope='UptoBPR',command_key='fresh-test',
            compatibility_digest='a'*64,runtime_reports=config,report_hooks=hook,publication_recipe='c'*64)
        run=NS(pk='owned')
        with patch('mta.runtime.input_reader.read_input',return_value={'scope_request':request}), \
                patch('mta.runtime.scope_runtime_reports.require_test_database'), \
                patch('mta.runtime.scope_runtime_reports.publication_configuration',return_value=({},hook,{})):
            self.assertEqual(module.configuration(run),(config,digest(request)))
            request['report_hooks']={'site_code':'FOREIGN'}
            with self.assertRaisesRegex(PublicationUnavailable,'hook_differs'):module.configuration(run)
            request['report_hooks']=hook
            request['extra']='forged'
            with self.assertRaisesRegex(PublicationUnavailable,'request_required'):module.configuration(run)

    def test_old_configuration_does_not_enter_new_reference_binder(self):
        from mta.presentation import scoped_view
        row=NS(metadata={'runtime_reports':{'schema':'fresh-scoped-runtime-reports-reference-v1'}},
            digest='wrong',recipe_digest='wrong',report_generation=None)
        with patch.object(scoped_view,'verify_guards'),patch.object(module,'bind') as new:
            with self.assertRaises(PublicationUnavailable):scoped_view._bind(row,'expected')
            new.assert_not_called()

    def test_receipt_is_bound_to_exact_phase_configuration_and_request(self):
        receipt=NS(owner_kind='SCOPED_PHASE',phase_id='owned-phase',source_digest='phase-digest',
            configuration_digest='configuration',scope_request_digest='request')
        run=NS(pk='owned-run');phase=NS(pk='owned-phase',digest='phase-digest')
        with patch('mta.runtime.runtime_report_publication.read',return_value=receipt) as reader:
            self.assertIs(module.require_publication(run,phase,'configuration','request'),receipt)
            reader.assert_called_once_with('owned-run',placement='PostBPR',verify_bytes=False)
            for key in ('owner_kind','phase_id','source_digest','configuration_digest','scope_request_digest'):
                original=getattr(receipt,key);setattr(receipt,key,'foreign')
                with self.subTest(field=key),self.assertRaisesRegex(PublicationUnavailable,'owner_differs'):
                    module.require_publication(run,phase,'configuration','request')
                setattr(receipt,key,original)

    def test_new_configuration_dispatch_cannot_refresh_old_parent_or_relabel_recipe(self):
        from mta.presentation import scoped_view
        from mta.runtime.scope_runtime_reports import PUBLICATION_REFERENCE
        row=NS(metadata={'runtime_reports':{'schema':PUBLICATION_REFERENCE}},digest='wrong',
            recipe_digest=module.LEGACY_VIEW_RECIPE)
        with patch.object(scoped_view,'verify_guards'):
            with self.assertRaisesRegex(PublicationUnavailable,'refresh_not_released'):
                scoped_view._bind(row,'expected',retained_parent=True)
            with self.assertRaisesRegex(PublicationUnavailable,'identity_differs'):
                scoped_view._bind(row,'expected')

    def test_new_metadata_keeps_existing_graph_shape_and_never_mutates_old_metadata(self):
        from mta.presentation import scoped_view
        old=dict(schema='fresh-bpr-read-reference-v2',recipe_digest=module.LEGACY_VIEW_RECIPE,
            runtime_reports={'schema':'old'},bpr={'source':'owned'},transition=None)
        preserved=deepcopy(old)
        with patch.object(scoped_view,'_metadata',return_value=old):
            # The real helper builds a new metadata object on every call.
            actual=module.metadata(None,None,None,None,None,None,None)
        self.assertEqual({k:v for k,v in actual.items() if k!='recipe_digest'},
            {k:v for k,v in preserved.items() if k!='recipe_digest'})
        self.assertEqual(actual['schema'],'fresh-bpr-read-reference-v2')
        self.assertNotEqual(actual['recipe_digest'],module.LEGACY_VIEW_RECIPE)
        self.assertEqual(old,preserved)


class RuntimeReportRequestScopeTests(unittest.TestCase):
    def test_only_exact_two_download_selectors_enter_request_read_scope(self):
        from mta.presentation.request_scope import _read_route
        for name in ('Spike_Order_Dump','TotalReqReport_YYYY-MM-DD'):
            self.assertTrue(_read_route('/api/mta/DownloadReports/'+name))
            self.assertFalse(_read_route('/unrelated/'+name))
        for name in ('Spiker_Order_Dump.zip','TotalReqReport_2026-10-25.csv','spike_order_dump'):
            self.assertFalse(_read_route('/api/mta/DownloadReports/'+name))


class RuntimeReportForwardGuardTests(unittest.TestCase):
    def guard(self,body,*,publication=False):
        from importlib import import_module
        from mta.presentation import scoped_view
        frozen=import_module('mta.runtime.migrations.0218_scope_read_reference_guards')
        deny=frozen.SQL.split('CREATE FUNCTION mta.deny_scope_read_truncate()',1)[1].split(
            'AS $guard$',1)[1].split('$guard$;',1)[0]
        triggers=[(name,kind,function,'O',0,None,'',False,False,False,None,None,'mta')
            for name,kind,function in [('scope_read_no_truncate',34,'deny_scope_read_truncate'),
                ('scope_read_reference_guard',31,'guard_scope_read_reference')]]
        functions=[(name,value,False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True)
            for name,value in sorted({'deny_scope_read_truncate':deny,
                'guard_scope_read_reference':body}.items())]
        cursor=MagicMock();cursor.fetchall.side_effect=[triggers,functions,
            [('owned-ingestion',True,['search_path=pg_catalog, mta'])]]
        with patch.object(scoped_view.connection,'cursor') as opened, \
                patch('mta.runtime.ingestion_ownership.require_guard_coverage'), \
                patch('mta.runtime.ingestion_ownership.scoped_derived_body',return_value='owned-ingestion'), \
                patch('mta.runtime.scoped_remark_ownership.verified_business_rows',side_effect=lambda c,rows:rows):
            opened.return_value.__enter__.return_value=cursor
            scoped_view.verify_guards(publication=publication)

    def test_exact_old_guard_remains_readable_but_cannot_admit_new_publication_reference(self):
        from importlib import import_module
        old=import_module('mta.runtime.migrations.0228_scope_read_action_ownership').BODY
        self.guard(old)
        with self.assertRaisesRegex(PublicationUnavailable,'guard_body_differs'):
            self.guard(old,publication=True)

    def test_only_exact_forward_guard_supports_both_contexts(self):
        from importlib import import_module
        forward=import_module('mta.runtime.migrations.0230_runtime_report_publication_guards').READ_REFERENCE_BODY
        self.guard(forward);self.guard(forward,publication=True)
        with self.assertRaisesRegex(PublicationUnavailable,'guard_body_differs'):
            self.guard(forward+'\n-- unregistered body')
