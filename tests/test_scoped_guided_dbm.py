"""Finite mixed-owner Guided DBM checks; no native database qualification."""
from contextlib import nullcontext
from copy import deepcopy
import re
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import MagicMock, patch

from tests.test_scoped_btr import fixture, Codes
from mta.presentation import scoped_guided_dbm as subject, guided_dbm as reader, daily_native_prepared as native
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest


class ScopedGuidedDbmTests(unittest.TestCase):
    def setUp(self):
        self.btr = fixture()
        self.run = self.btr.run
        self.btr.sources.acceptance_id = 'bpr'
        self.btr.sources.acceptance_digest = 'a'*64
        self.btr.sources.action_revision = 2
        self.rows = {}; self.images = {}
        for path, fields in subject.REQUIRED.items():
            row = {name: (3 if kind=='bigint' else 'S' if name=='SKUCode' else 'W' if name in ('WhCode','WHCode','LocCode') else None)
                   for name,kind in fields.items()}
            self.rows[path] = [row]
            self.images[path] = dict(image=path, table='/'.join(subject.typed.CATALOG['bindings'][path]),
                count=1, digest=digest([row]),
                fields=[(name,name,'int' if kind=='bigint' else 'str') for name,kind in fields.items()])
        self.context = Obj(run=self.run, dbm={'DBMMaster':self.rows[subject.MASTER]})
        self.view = Obj(run=self.run, run_id=self.run.pk, bpr=Obj(sources=self.btr.sources),
            reference=Obj(metadata={'runtime_reports':{'schema':'fresh-registered-placement-read-configuration-v1'}}))
        self.btr.predecessor.production_manifest = {'images':{path:item for path,item in self.images.items() if path!=subject.MASTER}}
        self.bound = subject.GuidedDbmBinding(self.view,self.btr,self.context,
            self.btr.predecessor.production_manifest['images'])

    def test_binding_uses_current_bpr_or_existing_dbm_context_but_same_inherited_collection(self):
        with patch.object(subject.scoped_btr,'bind',return_value=self.btr), \
                patch.object(subject.scoped_dbm,'bind',return_value=self.context) as current, \
                patch('mta.presentation.hierarchy.selected_manifest',return_value=None):
            bound = subject.bind(self.view)
            current.assert_called_once_with('bpr',expected_digest='a'*64,action_revision=2)
            self.assertIs(bound.context,self.context)
            self.assertEqual(bound.query(subject.SOURCES['A'])[1], [self.btr.predecessor.pk,subject.SOURCES['A']])
            old_images = deepcopy(bound.images)
            current.reset_mock()
            self.view.dbm_context = Obj(run=self.run,dbm={'DBMMaster':[dict(self.rows[subject.MASTER][0],Norm=9)]})
            updated = subject.bind(self.view)
            current.assert_not_called()
            self.assertEqual(updated.images,old_images)
            self.assertNotEqual(updated.query(subject.MASTER),bound.query(subject.MASTER))
            self.view.dbm_context.run = Obj(pk='foreign')
            with self.assertRaisesRegex(PublicationUnavailable,'current_owner'): subject.bind(self.view)

    def test_inherited_generation_receipt_must_match_declared_predecessor(self):
        path = subject.SOURCES['A']; item = self.btr.predecessor.production_manifest['images'].pop(path)
        row = Obj(pk='generation',digest='b'*64,source_digest='c'*64,recipe_digest='d'*64,metadata={'images':{path:item}})
        self.btr.sources.inherited_btr = Obj(locator={'report_generation':dict(id='generation',digest=row.digest,
            source_digest=row.source_digest,recipe_digest=row.recipe_digest)})
        with patch.object(subject.scoped_btr,'bind',return_value=self.btr), \
                patch.object(subject.scoped_dbm,'bind',return_value=self.context), \
                patch('mta.presentation.hierarchy.selected_manifest',return_value=None), \
                patch('mta.presentation.operational_reports.generation',return_value=row):
            self.assertEqual(subject.bind(self.view).images[path],item)
            row.digest='e'*64
            with self.assertRaisesRegex(PublicationUnavailable,'generation_differs'): subject.bind(self.view)

    def test_missing_wrong_empty_and_nonempty_wire_sources_refuse(self):
        path = subject.SOURCES['A']; item = self.images[path]
        for changed in (None,dict(item,image='foreign'),dict(item,table='BTR/SkuAttributeData'),
                        dict(item,count=0,fields=[],digest='f'*64)):
            with self.assertRaises(PublicationUnavailable): subject._checked(path,changed)
        empty = dict(item,count=0,fields=[],digest=digest([]))
        self.bound.images[path] = subject._checked(path,empty)
        self.bound.validate_fields(path)
        sql, params = self.bound.query(path)
        self.assertIn('"SuggestionGenerationAge"',sql)
        self.assertEqual(params,[self.btr.predecessor.pk,path])
        observed = deepcopy(item)
        observed['fields'][-1] = ('SuggestionGenerationAge','SuggestionGenerationAge','str')
        self.bound.images[path] = observed
        with patch.object(subject.GuidedDbmBinding,'rows',return_value=[{'SuggestionGenerationAge':None}]):
            self.bound.validate_fields(path)
        with patch.object(subject.GuidedDbmBinding,'rows',return_value=[{'SuggestionGenerationAge':'3'}]):
            with self.assertRaisesRegex(PublicationUnavailable,'wire_differs'): self.bound.validate_fields(path)

    def test_occurrence_join_order_and_columns_match_actual_native_producer(self):
        aliases = {path:alias for alias,path in subject.SOURCES.items()}
        relation = lambda path: ('SELECT '+aliases[path],[aliases[path]])
        with patch.object(subject.GuidedDbmBinding,'query',side_effect=relation), \
                patch.object(native,'image_metadata',side_effect=lambda _run,path:self.images[path]), \
                patch.object(native,'image_query',side_effect=lambda _run,path:relation(path)):
            selected, params = self.bound.occurrence_query()
            inserted, native_params = native._dbm_insert_query(self.run)
        self.assertEqual(params,native_params[:-1])
        self.assertEqual(selected.partition(' SELECT row_number')[0],inserted.partition(' INSERT INTO ')[0])
        self.assertEqual(selected.partition(' FROM A ')[2],inserted.partition(' FROM A ')[2])
        projection = selected.split(' SELECT row_number',1)[1].split(' FROM A ',1)[0]
        projection = 'row_number'+projection
        projection = re.sub(r'(?:::text|::bigint)? AS "[^"]+"','',projection)
        expected = inserted.split(') SELECT %s,',1)[1].split(' FROM A ',1)[0]
        self.assertEqual(projection,expected)
        self.assertNotIn('INSERT INTO',selected)

    def test_four_query_variants_preserve_full_aggregate_filter_and_sort_sql(self):
        attrs = {'SkuAttributeData':[], 'LocationAttributeData':[]}
        with patch.object(reader,'scope',return_value=(Codes(['S']),Codes(['W']))), \
                patch.object(reader,'_prepared_query',return_value=('SELECT * FROM occurrence',['occurrence'])), \
                patch.object(reader,'image_query',side_effect=lambda _run,path:('SELECT * FROM description',[path])), \
                patch.object(subject.GuidedDbmBinding,'occurrence_query',return_value=('SELECT * FROM occurrence',['occurrence'])), \
                patch.object(subject.GuidedDbmBinding,'query',side_effect=lambda path:('SELECT * FROM description',[path])):
            for kind in reader.KINDS:
                self.assertEqual(reader.build_query(self.run,{'filters':{}},kind,attrs),
                    reader.build_query(self.run,{'filters':{}},kind,attrs,read_binding=self.bound))

    def test_reader_skips_full_receipt_only_for_explicit_matching_phase_binding(self):
        attrs = {'SkuAttributeData':[], 'LocationAttributeData':[]}
        cursor = MagicMock(); cursor.__enter__.return_value=cursor
        cursor.fetchone.return_value=('on',)
        cursor.description=[('suggestion',),('count',),('first_ordinal',)]
        cursor.fetchall.return_value=[('Increase',2,0),(None,1,1)]
        with patch.object(subject.GuidedDbmBinding,'attributes',return_value=attrs), \
                patch.object(reader,'_require_prepared',side_effect=AssertionError('Full preparation')), \
                patch.object(reader,'build_query',return_value=('SELECT current_join',[])) as query, \
                patch.object(reader.transaction,'atomic',return_value=nullcontext()), \
                patch.object(reader.connection,'cursor',return_value=cursor):
            result=reader.read_guided_dbm(self.run,{},'pie',attrs,read_binding=self.bound)
            self.assertEqual(result,[{'suggestion':'Increase','count':2},{'count':1}])
            query.assert_called_once_with(self.run,{},'pie',attrs,read_binding=self.bound)
            with self.assertRaisesRegex(PublicationUnavailable,'binding_differs'):
                reader.read_guided_dbm(Obj(pk='foreign'),{},'pie',attrs,read_binding=self.bound)
            with self.assertRaises(AssertionError): reader.read_guided_dbm(self.run,{},'pie',attrs)
