"""Mixed stage ownership and unchanged BTR SQL bag semantics, without a DB."""
from copy import deepcopy
from datetime import date
import os
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch,MagicMock
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','scoped-btr-unit-only')
import django
django.setup()
from mta.presentation import scoped_btr, btr_sql, buffer_trends_sql
from mta.presentation.context import PublicationUnavailable


class Codes(set):
    @property
    def multiplicities(self):return {value:2 for value in self}


def fixture():
    parent=NS(pk=uuid4(),business_date=date(2026,10,23))
    run=NS(pk=uuid4(),predecessor_id=parent.pk,business_date=date(2026,10,24))
    sources=NS(run=run,rows=MagicMock(return_value=[{'current':None}]),
        query=MagicMock(side_effect=lambda path:('SELECT * FROM current_'+path.rsplit('/',1)[1],['CURRENT'])))
    images={path:dict(image=path,table=table,count=0,digest='a'*64,fields=[])
        for path,table in scoped_btr.INHERITED.items()}
    return scoped_btr.BtrBinding(sources,parent,images)


class ScopedBtrTests(unittest.TestCase):
    def test_current_aliases_and_inherited_physical_owner_are_not_substituted(self):
        binding=fixture()
        for path in scoped_btr.CURRENT:
            self.assertEqual(binding.query(path)[1],['CURRENT'])
            self.assertEqual(binding.rows(path),[{'current':None}])
        path='closing/btr/BufferTrendPhysicalInv'
        sql,params=binding.query(path)
        self.assertEqual(params,[binding.predecessor.pk,path])
        self.assertNotIn(binding.run.pk,params)
        self.assertIn('vf_ordinal',sql)
        rows=[dict(SKUCode='A',WhCode='X',D90=None),dict(SKUCode='A',WhCode='X',D90=None)]
        with patch.object(scoped_btr.typed,'load_image',return_value=rows) as load:
            self.assertEqual(binding.rows(path),rows)
            load.assert_called_once_with(binding.predecessor,binding.images[path])
        with self.assertRaises(PublicationUnavailable):binding.query('closing/btr/Invented')

    def test_inherited_metadata_cannot_change_path_table_or_column_owner(self):
        path='closing/btr/BufferTrendDates'
        item=fixture().images[path]
        for change in (dict(image='other'),dict(table='BTR/BufferTrendPhysicalInv'),
                dict(count=1),dict(fields=[['D90','SKUCode','str']])):
            with self.subTest(change=change),self.assertRaises(PublicationUnavailable):
                scoped_btr._checked(path,dict(item,**change))

    def test_binding_requires_existing_exact_predecessor_and_report_receipt(self):
        binding=fixture();sources=binding.sources
        phase=NS(pk=uuid4());sources.acceptance_id=phase.pk;sources.acceptance_digest='b'*64
        report=NS(pk=uuid4(),digest='c'*64,source_digest='d'*64,recipe_digest='e'*64,
            metadata={'images':binding.images})
        provenance=dict(owner_kind='PREDECESSOR',representation='physical',
            report_generation=dict(id=str(report.pk),digest=report.digest,
                source_digest=report.source_digest,recipe_digest=report.recipe_digest))
        inherited=NS(owner=binding.predecessor,locator=provenance,provenance=lambda:deepcopy(provenance))
        sources.inherited_btr=inherited
        binding.predecessor.production_manifest={'images':dict(binding.images)}
        # The actual native v3 owner stores trend analytics in its READY report.
        del binding.predecessor.production_manifest['images']['closing/btr/BPPTrendPhysicalInv']
        view=NS(bpr=NS(sources=sources))
        with patch('mta.runtime.scoped_pick_files._accepted',return_value=phase), \
                patch('mta.presentation.scoped_inherited_btr.bind',return_value=inherited), \
                patch('mta.presentation.operational_reports.generation',return_value=report) as generation:
            result=scoped_btr.bind(view)
            self.assertEqual(result.predecessor.pk,binding.predecessor.pk)
            generation.assert_called_once_with(binding.predecessor)
            report.digest='f'*64
            with self.assertRaisesRegex(PublicationUnavailable,'report_generation_differs'):
                scoped_btr.bind(view)
            provenance['owner_kind']='INITIALIZATION'
            with self.assertRaisesRegex(PublicationUnavailable,'predecessor_required'):
                scoped_btr.bind(view)

    def reader(self, *, count):
        run=NS(pk=uuid4(),business_date=date(2026,10,24))
        dates={f'D{i}':'2026-10-23' for i in range(1,91)}
        def rows(path):
            if path.endswith('BufferTrendDates'):return [dates]
            if path.endswith('CategoryColDescription'):return []
            if path.endswith('SKULocStandardAttributes'):return []
            return []
        binding=NS(run=run,rows=MagicMock(side_effect=rows),query=MagicMock(
            side_effect=lambda path:('SELECT * FROM '+('CURRENT' if path in scoped_btr.CURRENT else 'PREDECESSOR')+
                '_'+path.rsplit('/',1)[1],[path])))
        cursor=MagicMock();cursor.__enter__.return_value=cursor
        cursor.fetchone.return_value=(7,)
        cursor.description=[('Norm',),('D90',),('CD90',)]
        cursor.fetchall.return_value=[(None,12,'Green'),(None,12,'Green')]
        with patch.object(btr_sql.connection,'cursor',return_value=cursor), \
                patch.object(btr_sql,'scope',return_value=(Codes(['A']),Codes(['X']))), \
                patch.object(btr_sql.hierarchy,'selected_manifest',return_value=None), \
                patch('mta.presentation.btr_reporting.selected_generation',side_effect=AssertionError('parent prepared joins')):
            result=btr_sql.read_btr(run,{},paging=(1,10),count=count,read_binding=binding)
        return result,cursor,binding

    def test_count_uses_full_current_requirement_and_duplicate_permission_memberships(self):
        result,cursor,_=self.reader(count=True)
        self.assertEqual(result,dict(TechCount='7',EcoCount='7'))
        for call in cursor.execute.call_args_list:
            sql,params=call.args
            self.assertIn('CURRENT_vf_RationedReqReport',sql)
            self.assertIn('CURRENT_SKULocStandardAttributes',sql)
            self.assertIn('PREDECESSOR_BPPTrend',sql)
            self.assertIn('E AS (SELECT * FROM R)',sql)
            self.assertEqual(params.count('A'),2)
            self.assertEqual(params.count('X'),2)

    def test_grid_keeps_actual_labels_sql_null_wire_and_two_pass_duplicates(self):
        result,cursor,_=self.reader(count=False)
        self.assertEqual(result['labels'][0]['D90'],'2026-10-23')
        self.assertEqual(result['tech'],[dict(Norm='',D90='12',CD90='Green')]*2)
        self.assertEqual(result['eco'],result['tech'])
        for call in cursor.execute.call_args_list:
            sql,_=call.args
            self.assertIn('CURRENT_vf_RationedReqReport',sql)
            self.assertIn('FROM selected t JOIN A',sql)
            self.assertIn('LIMIT %s OFFSET %s',sql)
            self.assertIn('LEFT JOIN',sql)

    def test_full_reader_still_consults_its_original_prepared_generation(self):
        sentinel=RuntimeError('original Full generation')
        with patch('mta.presentation.btr_reporting.selected_generation',side_effect=sentinel):
            with self.assertRaisesRegex(RuntimeError,'original Full'):
                btr_sql.read_btr(NS(pk=uuid4()),{},paging=(1,10))

    def test_graph_uses_inherited_dates_without_full_prepared_admission(self):
        run=NS(pk=uuid4())
        dates=[dict(D90='2026-10-23')]
        binding=NS(run=run,rows=MagicMock(side_effect=lambda path:dates if path.endswith('BufferTrendDates') else []))
        with patch.object(buffer_trends_sql,'scope',return_value=(Codes(),Codes())), \
                patch.object(buffer_trends_sql.hierarchy,'selected_manifest',return_value=None), \
                patch('mta.presentation.history_prepared_sql.admitted',side_effect=AssertionError('Full admission')), \
                patch.object(buffer_trends_sql,'graph_response',return_value={'inherited':True}) as response:
            self.assertEqual(buffer_trends_sql.read_graph(run,{'Days':1},read_binding=binding),{'inherited':True})
            self.assertEqual(response.call_args.args[1],dates)
