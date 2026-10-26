"""Scoped Chronic source and unchanged native query contracts (no DB proof)."""
from contextlib import nullcontext
from copy import deepcopy
import re
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import MagicMock, patch

from tests.test_scoped_btr import fixture, Codes
from mta.presentation import scoped_guided_chronic as subject
from mta.presentation import guided_chronic as grid, chronic_sql as charts, daily_native_prepared as native
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest


class ScopedChronicTests(unittest.TestCase):
    def setUp(self):
        self.btr = fixture()
        self.run = self.btr.run
        self.images = {}
        for path in subject.REQUIRED:
            table = '/'.join(subject.typed.CATALOG['bindings'][path])
            fields = [(name,name,subject.WIRE[kind]) for name,kind in subject.typed.CATALOG['tables'][table]]
            self.images[path] = dict(image=path,table=table,count=1,digest='a'*64,fields=fields)
        self.btr.predecessor.production_manifest = {'images':{path:item for path,item in self.images.items() if path!=subject.NMS}}
        self.btr.sources.metadata = MagicMock(side_effect=lambda path:self.images[path])
        self.view = Obj(run=self.run,run_id=self.run.pk,bpr=Obj(sources=self.btr.sources),
            reference=Obj(metadata={'runtime_reports':{'schema':'fresh-registered-placement-read-configuration-v1'}}))
        self.bound = subject.ChronicBinding(self.view,self.btr,'chronic-grid',self.images)

    def test_grid_uses_current_nms_but_charts_only_inherited_facts_and_descriptions(self):
        with patch.object(subject.scoped_btr,'bind',return_value=self.btr), \
                patch('mta.presentation.hierarchy.selected_manifest',return_value=None):
            for kind in subject.KINDS:
                with self.subTest(kind=kind):
                    self.btr.sources.metadata.reset_mock()
                    bound = subject.bind(self.view,kind)
                    self.assertEqual(bound.query(subject.FACT)[1],[self.btr.predecessor.pk,subject.FACT])
                    if kind=='chronic-grid':
                        self.assertEqual(bound.query(subject.NMS),self.btr.sources.query(subject.NMS))
                    else:
                        self.btr.sources.metadata.assert_not_called()
                        with self.assertRaises(PublicationUnavailable):bound.query(subject.NMS)
                        with self.assertRaises(PublicationUnavailable):bound.occurrence_query()
            self.images[subject.NMS]['table']='BTR/ChronicUnavalabilityData'
            with self.assertRaisesRegex(PublicationUnavailable,'current_nms_owner'):
                subject.bind(self.view,'chronic-grid')

    def test_declared_empty_and_bad_nonempty_wire(self):
        original = deepcopy(self.images[subject.FACT])
        self.images[subject.FACT].update(count=0,fields=[],digest=digest([]))
        self.assertIn(('RLT','RLT','int'),self.bound.metadata(subject.FACT)['fields'])
        self.assertIn('"RLT"',self.bound.query(subject.FACT)[0])
        self.images[subject.FACT]['digest']='e'*64
        with self.assertRaisesRegex(PublicationUnavailable,'empty_digest'):self.bound.metadata(subject.FACT)
        self.images[subject.FACT] = original
        original['fields']=[(n,c,'str' if n=='RLT' else wire) for n,c,wire in original['fields']]
        with self.assertRaisesRegex(PublicationUnavailable,'wire_differs'):self.bound.metadata(subject.FACT)

    def test_occurrence_sql_matches_actual_native_producer(self):
        aliases={path:owner for owner,path in subject.SOURCES.items()}
        relation=lambda path:('SELECT '+aliases[path],[aliases[path]])
        with patch.object(subject.ChronicBinding,'query',side_effect=relation), \
                patch.object(native,'image_metadata',side_effect=lambda _run,path:self.images[path]), \
                patch.object(native,'image_query',side_effect=lambda _run,path:relation(path)):
            actual,params=self.bound.occurrence_query()
            expected,native_params=native._chronic_insert_query(self.run)
        self.assertEqual(params,native_params[:-1])
        self.assertEqual(actual.partition(' SELECT row_number')[0],expected.partition(' INSERT INTO ')[0])
        self.assertEqual(actual.partition(' FROM A ')[2],expected.partition(' FROM A ')[2])
        selected='row_number'+actual.split(' SELECT row_number',1)[1].split(' FROM A ',1)[0]
        selected=re.sub(r' AS "[^"]+"','',selected)
        self.assertEqual(selected,expected.split(') SELECT %s,',1)[1].split(' FROM A ',1)[0])
        self.assertNotIn('INSERT INTO',actual)

    def test_grid_filter_parent_and_permission_queries_preserve_full_contract(self):
        attrs={'SkuAttributeData':[], 'LocationAttributeData':[]}
        payloads=[{}, {'filters':{'supplyChainFilter':{'filters':[{'attributeName':'forChildren','value':'Parent'}]},
            'customAttributeFilter':{'filters':[{'attributeName':'skulocattr1','value':'pair','operator':'equalto'}]}}}]
        relation=lambda path:('SELECT * FROM source',[path])
        with patch.object(grid,'scope',return_value=(Codes(['S']),Codes(['W']))), \
                patch.object(grid,'_prepared_query',return_value=('SELECT * FROM occurrences',['rows'])), \
                patch.object(grid,'image_metadata',side_effect=lambda _run,path:self.images[path]), \
                patch.object(grid,'image_query',side_effect=lambda _run,path:relation(path)), \
                patch.object(subject.ChronicBinding,'occurrence_query',return_value=('SELECT * FROM occurrences',['rows'])), \
                patch.object(subject.ChronicBinding,'query',side_effect=relation):
            for payload in payloads:
                self.assertEqual(grid.build_query(self.run,payload,attrs),
                    grid.build_query(self.run,payload,attrs,read_binding=self.bound))

    def test_grid_response_preserves_duplicates_numeric_wire_nulls_and_jit(self):
        fields=[('skucode','str'),('RLT','int'),('PhysicalInventoryPen','str'),('PipelineInventoryPen','str'),('_copies','int')]
        cursor=MagicMock();cursor.__enter__.return_value=cursor
        cursor.fetchone.return_value=('on',);cursor.fetchall.return_value=[('S',2,'12.50',None,2)]
        with patch.object(subject.ChronicBinding,'attributes',return_value={'SkuAttributeData':[],'LocationAttributeData':[]}), \
                patch.object(grid,'_require_prepared',side_effect=AssertionError('Full receipt')), \
                patch.object(grid,'build_query',return_value=('SELECT rows',[],fields)), \
                patch.object(grid.transaction,'atomic',return_value=nullcontext()), \
                patch.object(grid.connection,'cursor',return_value=cursor):
            result=grid.read_guided_chronic(self.run,{},read_binding=self.bound)
            self.assertEqual(result,[dict(skucode='S',RLT=2,PhysicalInventoryPen=12.5)]*2)
            self.assertIsNot(result[0],result[1])
            self.assertEqual(cursor.execute.call_args.args,("SELECT set_config('jit',%s,true)",['on']))
            with self.assertRaisesRegex(PublicationUnavailable,'binding_differs'):
                grid.read_guided_chronic(Obj(pk='foreign'),{},read_binding=self.bound)
            with self.assertRaises(AssertionError):grid.read_guided_chronic(self.run,{})

    def test_chart_sql_matches_default_and_empty_does_not_query(self):
        self.run.kind='LEGACY_UI_FIXTURE'
        attrs={'SkuAttributeData':[], 'LocationAttributeData':[]}
        cursor=MagicMock();cursor.__enter__.return_value=cursor
        cursor.fetchone.return_value=('on','on');cursor.fetchall.return_value=[]
        relation=lambda path:('SELECT * FROM source',[path])
        with patch.object(charts,'native_fixture',return_value=True), \
                patch('mta.presentation.daily_preparation.production_branch',return_value=False), \
                patch.object(charts,'scope',return_value=(Codes(['S']),Codes(['W']))), \
                patch.object(charts,'image_rows',return_value=[]), \
                patch.object(charts,'image_metadata',side_effect=lambda _run,path:self.images[path]), \
                patch.object(charts,'image_query',side_effect=lambda _run,path:relation(path)), \
                patch.object(subject.ChronicBinding,'rows',return_value=[]) as rows, \
                patch.object(subject.ChronicBinding,'query',side_effect=relation), \
                patch.object(charts.transaction,'atomic',return_value=nullcontext()), \
                patch.object(charts.connection,'cursor',return_value=cursor):
            for kind in ('chronic-sku','chronic-loc'):
                bound=subject.ChronicBinding(self.view,self.btr,kind,self.images)
                for payload in ({},{'supplyChainFilter':{'filters':[{'attributeName':'forChildren','value':'Parent'}]}}):
                    cursor.execute.reset_mock()
                    charts.read_chronic(self.run,payload,kind)
                    expected=cursor.execute.call_args_list
                    cursor.execute.reset_mock()
                    self.assertEqual(charts.read_chronic(self.run,payload,kind,read_binding=bound),[])
                    self.assertEqual(cursor.execute.call_args_list,expected)
            self.images[subject.FACT].update(count=0,fields=[],digest=digest([]))
            cursor.execute.reset_mock()
            self.assertEqual(charts.read_chronic(self.run,{},kind,read_binding=bound),[])
            cursor.execute.assert_not_called()
            rows.assert_called_with(subject.FACT)
