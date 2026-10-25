"""BOR read bindings: immutable owners, policy gate and retained SQL behavior."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'scoped-bor-unit-only')
import django
django.setup()
from contextlib import ExitStack
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from django.test import override_settings
from mta.presentation import scoped_bor, bor_sql, boroa_sql, bor_preparation, boroa_preparation
from mta.presentation.context import PublicationUnavailable
from mta.presentation.permissions import PermissionCodes
from mta.application import production_output_policy
from test_production_bor_contract import supplier
from test_production_output_policy import core


class ScopedBorReadsTests(unittest.TestCase):
    def view(self):
        run=NS(pk='run')
        source=NS(run=run,acceptance_id='phase',acceptance_digest='phase-digest',snapshot_digest='snapshot')
        return NS(run=run,run_id=run.pk,bpr=NS(sources=source))

    def declaration(self):
        return dict(purpose='owned-scoped-test',run_id='run',phase_id='phase',
            phase_digest='phase-digest',snapshot_digest='snapshot',output_contract=production_output_policy.contract())

    def binding(self):
        view=self.view()
        return scoped_bor.BorBinding(view.run,view,NS(),production_output_policy.contract())

    def test_policy_requires_exact_test_declaration(self):
        with patch('mta.runtime.scope_runtime_reports.require_test_database') as test_db:
            with override_settings(VF_MTA_SCOPED_BOR_OUTPUT_POLICY=None):
                with self.assertRaises(PublicationUnavailable):scoped_bor.policy(self.view())
            declaration=self.declaration()
            with override_settings(VF_MTA_SCOPED_BOR_OUTPUT_POLICY=declaration):
                self.assertEqual(scoped_bor.policy(self.view()),declaration)
            test_db.assert_called_once()
            declaration['phase_digest']='other'
            with override_settings(VF_MTA_SCOPED_BOR_OUTPUT_POLICY=declaration):
                with self.assertRaises(PublicationUnavailable):scoped_bor.policy(self.view())

    def test_binding_requires_selected_view_and_current_revision_owner(self):
        from mta.presentation.scoped_view import ViewBinding
        view=self.view();source=view.bpr.sources
        source.action_revision=3;source.source_digest='source'
        selected=ViewBinding(NS(),view.bpr,None,None,None)
        with patch.object(scoped_bor,'policy',return_value=self.declaration()), \
                patch('mta.presentation.scoped_sources.bind',return_value=source) as bind, \
                patch('mta.presentation.scoped_sources._accepted_phase',return_value=NS()):
            result=scoped_bor.require_binding(view.run,selected)
            self.assertIs(result.run,view.run)
            bind.assert_called_once_with('phase',expected_digest='phase-digest',action_revision=3)
            with self.assertRaises(PublicationUnavailable):scoped_bor.require_binding(NS(pk='other'),selected)
            with self.assertRaises(PublicationUnavailable):scoped_bor.require_binding(view.run,view)
            bind.side_effect=PublicationUnavailable('revision changed')
            with self.assertRaisesRegex(PublicationUnavailable,'revision changed'):
                scoped_bor.require_binding(view.run,selected)

    def test_normal_projection_preserves_duplicate_supplier_order_denies_duplicate_colours(self):
        bound=self.binding()
        source=[supplier(),supplier(SupplierCode='second')]
        bound.view.bpr.sources.rows=Mock(return_value=[dict(SKUCode='SKU-1',WhCode='TOP',DispatchColor='Black')])
        with patch.object(scoped_bor.BorBinding,'_image',return_value=(source,('',[]))), \
                patch.object(scoped_bor,'_values',side_effect=lambda rows,fields:rows):
            rows=bound.source_query('SupplierDispatchReq')
            self.assertEqual([row['SupplierCode'] for row in rows],['SUP','second'])
            self.assertEqual([row['DispatchReq'] for row in rows],[17,17])
            self.assertEqual([row['ReqTopOfBlack'] for row in rows],[7,7])
            self.assertEqual([row['ReqTopOfRed'] for row in rows],[0,0])
            self.assertEqual(source[0]['ReqTopOfRed'],7)
            bound.view.bpr.sources.rows.return_value*=2
            with self.assertRaises(PublicationUnavailable):bound.source_query('SupplierDispatchReq')

    def test_oa_projection_keeps_known_and_empty_text_nulls_only_missing(self):
        bound=self.binding();row=core();row.update(SKULocAtt04='known',SKULocAtt15='')
        with patch.object(scoped_bor.BorBinding,'_image',return_value=([row,row],('',[]))), \
                patch.object(scoped_bor,'_values',side_effect=lambda rows,fields:rows):
            rows=bound.source_query('BORWithOrderAllocation')
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[0]['SKULocAtt04'],'known')
            self.assertEqual(rows[0]['SKULocAtt15'],'')
            self.assertIsNone(rows[0]['SKULocAtt01'])
            row.pop('Norm')
            with self.assertRaises(PublicationUnavailable):bound.source_query('BORWithOrderAllocation')

    def test_three_field_requirement_uses_exact_same_producer_parent_without_changing_bag(self):
        bound=self.binding()
        requirement=[dict(SKUCode='S',WhCode='B',AdvAllocDone=3),dict(SKUCode='S',WhCode='A',AdvAllocDone=4)]
        report=[dict(SKUCode='S',WhCode='A',ParentWhCode=None),dict(SKUCode='S',WhCode='B',ParentWhCode='')]
        master=[dict(SKUCode='S',WHCode='A',ParentWhCode=None),dict(SKUCode='S',WHCode='B',ParentWhCode='')]
        populations={'reports/bpr/vf_RationedReqReport':report,'closing/bpr/BPRMaster':master}
        bound.view.bpr.sources.rows=Mock(side_effect=populations.__getitem__)
        item=dict(fields=[[name,name,'str' if name!='AdvAllocDone' else 'int']
                          for name in ('SKUCode','WhCode','AdvAllocDone')])
        bound.phase.snapshot=NS(manifest=dict(consumers=dict(production_reports=dict(BOROARequirement=dict(image='owned'))),
                                              images={'owned':item}))
        with patch.object(scoped_bor.BorBinding,'_image',return_value=(requirement,('original',[]))), \
                patch.object(scoped_bor,'_values',side_effect=lambda rows,fields:rows):
            projected=bound.source_query('BOROARequirement')
        self.assertEqual(projected,[dict(requirement[0],ParentWhCode=''),dict(requirement[1],ParentWhCode=None)])
        self.assertNotIn('ParentWhCode',requirement[0])
        for invalid_report,invalid_master,invalid_requirement in (
                (report+report[:1],master,requirement),
                (report,master+master[:1],requirement),
                (report[:-1],master,requirement),
                (report,master,requirement+requirement[:1]),
                (report,[dict(master[0],ParentWhCode='changed'),master[1]],requirement),
                ([dict(report[0],SKUCode='s'),report[1]],master,requirement)):
            populations['reports/bpr/vf_RationedReqReport']=invalid_report
            populations['closing/bpr/BPRMaster']=invalid_master
            with self.assertRaises(PublicationUnavailable):bound._requirement_parents(invalid_requirement)

    def test_known_requirement_parent_uses_original_relation(self):
        bound=self.binding()
        bound.phase.snapshot=NS(manifest=dict(consumers=dict(production_reports=dict(BOROARequirement=dict(image='owned'))),
            images={'owned':dict(fields=[['ParentWhCode','ParentWhCode','str']])}))
        with patch.object(scoped_bor.BorBinding,'_image',return_value=([],('original',[]))), \
                patch.object(scoped_bor.BorBinding,'_requirement_parents',side_effect=AssertionError('reprojected known source')):
            self.assertEqual(bound.source_query('BOROARequirement'),('original',[]))

    def test_preparation_binding_retains_original_joins_without_full_owners(self):
        bound=Mock()
        bound.source_query.side_effect=lambda name:('SELECT * FROM owned_'+name,[name])
        bound.image_query.side_effect=lambda path:('SELECT * FROM owned_dimension',[path])
        for module in (bor_preparation,boroa_preparation):
            with patch.object(module,'admitted_sources',side_effect=AssertionError('Full admission')):
                sql,params,columns=module.query(NS(pk='run'),read_binding=bound)
            self.assertIn('vf_ordinal NULLS FIRST',sql)
            self.assertIn('LEFT JOIN',sql)
            self.assertIn('supplier_key',columns)
            self.assertNotIn('run_id=%s',sql)

    def test_reader_scope_multiplicity_count_and_export_keep_existing_sql(self):
        view=self.view();bound=Mock()
        bound.attributes.return_value={'SkuAttributeData':[],'LocationAttributeData':[]}
        bound.remarks.return_value=('SELECT * FROM owned_remark',['capture'])
        bound.configuration.return_value={'environment':[dict(ConfigKey='BOROA_DISPATCH_CONDITION',Category='ClientSpecific',ConfigValue='1')]}
        for reader,preparation,name in ((bor_sql,bor_preparation,'read_bor'),(boroa_sql,boroa_preparation,'read_boroa')):
            cursor=Mock();cursor.fetchone.return_value=(6,);cursor.description=[('SOB',)];cursor.fetchall.return_value=[(100.0,)]
            with ExitStack() as stack:
                stack.enter_context(patch.object(scoped_bor,'require_binding',return_value=bound))
                stack.enter_context(patch.object(reader,'admitted_sources',side_effect=AssertionError('Full admission')))
                stack.enter_context(patch.object(reader,'scope',return_value=(PermissionCodes({'SKU':2}),PermissionCodes({'WH':3})) ))
                stack.enter_context(patch.object(preparation,'query',return_value=('SELECT * FROM owned_prepared',['phase'],[])))
                cm=Mock();cm.__enter__=Mock(return_value=cursor);cm.__exit__=Mock(return_value=False)
                stack.enter_context(patch.object(reader.connection,'cursor',return_value=cm))
                self.assertEqual(getattr(reader,name)({},count=True,read_binding=view),6)
                sql,params=cursor.execute.call_args.args
                self.assertIn('owned_prepared',sql);self.assertNotIn('R.run_id=',sql)
                self.assertEqual(params[:5],['SKU','SKU','WH','WH','WH'])
                if reader is boroa_sql:self.assertIn('SELECT DISTINCT',sql)
                getattr(reader,name)({},export=True,read_binding=view)
                sql,_=cursor.execute.call_args.args
                self.assertIn('LEFT JOIN RM',sql);self.assertNotIn('LIMIT',sql)

    def test_default_readers_keep_full_admission(self):
        for module,name in ((bor_sql,'read_bor'),(boroa_sql,'read_boroa')):
            with patch.object(module,'admitted_sources',side_effect=PublicationUnavailable('Full owner required')) as admission, \
                    patch.object(scoped_bor,'require_binding',side_effect=AssertionError('scoped reached')):
                with self.assertRaisesRegex(PublicationUnavailable,'Full owner required'):
                    getattr(module,name)({})
                admission.assert_called_once_with()

    def test_logical_manifest_uses_physical_pre_image_and_denies_missing_fields(self):
        bound=self.binding()
        item=dict(table='BPR/SOBData',image='phase/PRE_BPR/supplier/sob',count=0,
                  digest='0'*64,fields=[])
        bound.phase.snapshot=NS(manifest=dict(state=dict(supplier_sob=dict(image='phase/BPR/supplier/sob')),
                                              images={'phase/BPR/supplier/sob':item}))
        with patch.object(scoped_bor,'load_image',return_value=[]):
            sql,params=bound.source_query('SOBData')
            self.assertEqual(params,['run','phase/PRE_BPR/supplier/sob'])
            self.assertIn('vf_image=%s',sql)
            item['count']=1
            item['fields']=[['SKUCode','SKUCode','str']]
            with self.assertRaises(PublicationUnavailable):bound.source_query('SOBData')

    def test_remarks_require_current_capture_without_live_or_predecessor(self):
        bound=self.binding()
        with patch('mta.presentation.ancillary_live.image_rows',return_value=[]) as rows, \
                patch('mta.presentation.ancillary_live.image_query',return_value=('owned',[])) as query:
            self.assertEqual(bound.remarks('BORReport_RemarkDetails'),('owned',[]))
            self.assertFalse(rows.call_args.kwargs['include_live'])
            self.assertFalse(query.call_args.kwargs['include_live'])
            rows.side_effect=PublicationUnavailable('capture missing')
            with self.assertRaises(PublicationUnavailable):bound.remarks('BORReport_RemarkDetails')


if __name__=='__main__':unittest.main()
