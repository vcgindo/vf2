"""Current RRR allocation reads require the exact selected phase source."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','scoped-rrr-unit-only')
import django
django.setup()
from contextlib import ExitStack
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from mta.presentation import daily_rrr_read as reader, scoped_bor
from mta.presentation.context import PublicationUnavailable
from mta.presentation.permissions import PermissionCodes
from mta.presentation.daily_rrr_colour import OUTPUT_FIELDS


class ScopedDailyRrrReadsTests(unittest.TestCase):
    def fixture(self):
        view=NS(run=NS(pk='run'))
        bound=Mock()
        bound._image.return_value=([dict(Requirement=None)],('SELECT * FROM owned_current_rrr',['phase-image']))
        bound.attributes.return_value={
            'SkuAttributeData':[dict(SL1=None,SL2='known',SL3='')],
            'LocationAttributeData':[dict(LL1='known',LL2=None,LL3='')]}
        def metadata(path):
            table='Importer/'+path.rsplit('/',1)[-1]
            return dict(table=table,count=1,fields=[[name,name,'str'] for name,_ in reader.CATALOG['tables'][table]])
        bound.view.bpr.sources.metadata.side_effect=metadata
        bound.image_query.side_effect=lambda path:('SELECT * FROM owned_dimension',[path])
        cursor=Mock()
        cursor.description=[('Requirement',),('DispatchColor',)]
        cursor.fetchall.return_value=[(None,None),(None,None)]
        cursor.fetchone.return_value=(6,)
        cm=Mock();cm.__enter__=Mock(return_value=cursor);cm.__exit__=Mock(return_value=False)
        return view,bound,cursor,cm

    def context(self,bound,cm,*,products=None,locations=None):
        stack=ExitStack()
        stack.enter_context(patch.object(scoped_bor,'require_binding',return_value=bound))
        stack.enter_context(patch.object(reader,'image_rows',side_effect=AssertionError('Full rows reached')))
        stack.enter_context(patch.object(reader,'image_query',side_effect=AssertionError('Full query reached')))
        stack.enter_context(patch.object(reader.hierarchy,'selected_manifest',side_effect=AssertionError('Full hierarchy reached')))
        stack.enter_context(patch.object(reader,'scope',return_value=(
            products if products is not None else PermissionCodes({'SKU':2}),
            locations if locations is not None else PermissionCodes({'WH':3}))))
        stack.enter_context(patch.object(reader.connection,'cursor',return_value=cm))
        return stack

    def test_grid_count_export_use_exact_current_owner_with_original_nulls_and_multiplicity(self):
        view,bound,cursor,cm=self.fixture()
        payload=dict(paginationParameter=dict(pageNumber=2,recordsPerPage=3))
        with self.context(bound,cm):
            self.assertEqual(reader.read(view.run,payload,read_binding=view),
                             [dict(Requirement=None,DispatchColor=None)]*2)
            sql,params=cursor.execute.call_args.args
            self.assertIn('owned_current_rrr',sql)
            self.assertIn('LEFT JOIN B',sql);self.assertIn('LEFT JOIN S3',sql)
            self.assertIn('generate_series(1,weight)',sql)
            self.assertIn('"RN" BETWEEN %s AND %s',sql)
            self.assertEqual(params[-6:],['SKU',2,'WH',3,4,6])
            self.assertNotIn('RRR_OrderAllocationHistory',sql)
            self.assertEqual(reader.read(view.run,{},count=True,read_binding=view),6)
            self.assertNotIn('LEFT JOIN S3',cursor.execute.call_args.args[0])
            reader.read(view.run,payload,export=True,read_binding=view)
            self.assertNotIn('BETWEEN',cursor.execute.call_args.args[0])
        bound._image.assert_called_with(('consumers','production_reports','RRR_OrderAllocation'),
                                       'production/RRR_OrderAllocation',OUTPUT_FIELDS)

    def test_empty_permission_and_children_filters_preserve_original_predicates(self):
        view,bound,cursor,cm=self.fixture()
        payload=dict(filters=dict(supplyChainFilter=dict(filters=[
            dict(attributeName='forchildrenlocationcode',value='P'),
            dict(attributeName='forchildren',value='Plant')])))
        with self.context(bound,cm,products=PermissionCodes({})):
            reader.read(view.run,payload,read_binding=view)
        sql,params=cursor.execute.call_args.args
        self.assertIn('P AS (SELECT NULL::text AS code WHERE FALSE)',sql)
        self.assertIn('JOIN Dnative parent',sql)
        self.assertIn('A."ParentWhCode"',sql)
        self.assertEqual(params[-2:],['Plant','P'])

    def test_missing_source_field_or_dimension_denies_without_producing(self):
        view,bound,cursor,cm=self.fixture()
        with self.context(bound,cm):
            bound._image.side_effect=PublicationUnavailable('bpr_bor_source_fields_missing:production/RRR_OrderAllocation')
            with self.assertRaisesRegex(PublicationUnavailable,'RRR_OrderAllocation'):
                reader.read(view.run,{},read_binding=view)
            cursor.execute.assert_not_called()
            bound._image.side_effect=None
            bound.view.bpr.sources.metadata.side_effect=None
            bound.view.bpr.sources.metadata.return_value=dict(count=1,fields=[['SKUCode','SKUCode','str']])
            with self.assertRaisesRegex(PublicationUnavailable,'scoped_rrr_importer_fields_missing'):
                reader.read(view.run,{},read_binding=view)
            cursor.execute.assert_not_called()

    def test_changed_phase_revision_denies_before_sql(self):
        view,bound,cursor,cm=self.fixture()
        with patch.object(scoped_bor,'require_binding',side_effect=PublicationUnavailable('phase changed')):
            with self.assertRaisesRegex(PublicationUnavailable,'phase changed'):
                reader.read(view.run,{},read_binding=view)
        bound._image.assert_not_called()

    def test_default_path_keeps_original_full_admission(self):
        from mta.presentation import native_publication
        with patch.object(native_publication,'enabled',return_value=True), \
                patch.object(native_publication,'require_mode',side_effect=PublicationUnavailable('Full admission')) as admit, \
                patch.object(scoped_bor,'require_binding',side_effect=AssertionError('scoped reached')):
            with self.assertRaisesRegex(PublicationUnavailable,'Full admission'):reader.read(NS(pk='run'),{})
            admit.assert_called_once_with()


if __name__=='__main__':unittest.main()
