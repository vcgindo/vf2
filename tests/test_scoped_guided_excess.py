"""Mixed phase/terminal excess history query contracts, without native writes."""
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import MagicMock, patch

from tests.test_scoped_btr import fixture, Codes
from mta.presentation import scoped_guided_excess as subject, guided_history_prepared as reader
from mta.presentation import daily_native_prepared as native, insight_history_sql
from mta.presentation.insight_filters import InsightPredicate
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest


class ScopedExcessTests(unittest.TestCase):
    def setUp(self):
        self.btr=fixture();self.run=self.btr.run
        self.run.kind='DAILY_CHAIN'
        self.images={}
        for path in subject.PATHS:
            table='Importer/'+path.rsplit('/',1)[1]
            self.images[path]=dict(table=table,count=0,digest=digest([]),fields=[])
        self.btr.sources.metadata=MagicMock(side_effect=lambda path:self.images[path])
        self.reports=Obj(generation=Obj(run_id=self.run.pk),query=MagicMock(return_value=('SELECT * FROM current_excess',['current-generation'])))
        self.view=Obj(run=self.run,run_id=self.run.pk,bpr=Obj(sources=self.btr.sources,reports=self.reports),
            reference=Obj(metadata={'runtime_reports':{'schema':'fresh-registered-placement-read-configuration-v1'}}))
        self.history=dict(run_id=str(self.btr.predecessor.pk),storage_cutoff='2026-10-22',
            coverage_cutoff='2026-10-22',lineage=[dict(run_id=str(self.btr.predecessor.pk),ordinal=0)])
        self.bound=subject.ExcessBinding(self.view,self.btr.predecessor,self.history)

    def test_binding_requires_registered_current_and_actual_parent_chain(self):
        with patch.object(subject.scoped_btr,'bind',return_value=self.btr), \
                patch.object(subject.hierarchy,'selected_manifest',return_value=None), \
                patch.object(subject.native_excess_history,'identity',return_value=self.history) as identity:
            bound=subject.bind(self.view)
            self.assertEqual(bound.history,self.history)
            identity.assert_called_once_with(self.btr.predecessor)
            self.history['lineage'][0]['run_id']=str(self.run.pk)
            with self.assertRaisesRegex(PublicationUnavailable,'history_owner_differs'):subject.bind(self.view)
            identity.side_effect=PublicationUnavailable('native_guided_excess_projection_required')
            with self.assertRaisesRegex(PublicationUnavailable,'projection_required'):subject.bind(self.view)

    def test_fact_union_is_exact_current_generation_and_prior_owners(self):
        sql,params=self.bound.fact_query()
        self.assertEqual(params,['current-generation',[str(self.btr.predecessor.pk)]])
        self.assertIn('UNION ALL',sql)
        self.assertIn('WHERE run_id=ANY(%s::uuid[])',sql)
        self.assertIn('ordinal AS vf_ordinal',sql)
        self.assertNotIn(str(self.run.pk),sql)
        self.reports.query.assert_called_once_with('ExcessInventoryDetails')
        fields=self.bound.metadata(subject.PATHS[0])['fields']
        self.assertIn(('SKUCode','SKUCode','str'),fields)
        self.images[subject.PATHS[0]]['digest']='a'*64
        with self.assertRaisesRegex(PublicationUnavailable,'empty_digest'):self.bound.metadata(subject.PATHS[0])

    def test_history_join_and_ordinal_contract_match_actual_native_producer(self):
        relation=lambda path:('SELECT * FROM dimension',[path])
        current=str(self.run.pk);parent=str(self.btr.predecessor.pk)
        expected_history=dict(self.history,lineage=[dict(run_id=current,ordinal=0),dict(run_id=parent,ordinal=1)])
        cursor=MagicMock()
        with patch.object(subject.ExcessBinding,'query',side_effect=relation), \
                patch.object(native,'image_query',side_effect=lambda _run,path:relation(path)):
            actual,params=self.bound.history_query(self.run.business_date-timedelta(days=30))
            native._history_excess(cursor,self.run,expected_history)
        expected,original_params=cursor.execute.call_args.args
        native_join=expected.split('joined AS (',1)[1].split(') INSERT INTO ',1)[0]
        native_join=native_join.replace(subject.quote(subject.ExcessInventoryRow._meta.db_table),'facts')
        actual_join=actual.split('joined AS (',1)[1].split('),occurrences AS (',1)[0]
        self.assertEqual(actual_join,native_join)
        native_projection=expected.split('SELECT %s,row_number()',1)[1].split(' FROM joined',1)[0]
        actual_projection=actual.split('SELECT row_number()',1)[1].split(' FROM joined',1)[0]
        self.assertEqual(actual_projection.replace('-1 ordinal,','-1,'),native_projection)
        self.assertEqual(params[-6:-1],[current,0,parent,1,self.history['storage_cutoff']])
        self.assertEqual(params[-1],self.run.business_date-timedelta(days=30))
        self.assertNotIn('INSERT INTO',actual)

    def test_existing_aggregate_filter_and_permission_sql_preserved(self):
        attrs={'SkuAttributeData':[],'LocationAttributeData':[]}
        cutoff=self.run.business_date-timedelta(days=30)
        cursor=MagicMock();cursor.__enter__.return_value=cursor;cursor.fetchall.return_value=[]
        full_history=('SELECT * FROM mta.'+reader.quote(reader.GuidedExcessHistoryRow._meta.db_table)+
            ' WHERE run_id=%s AND report_date>%s',[self.run.pk,cutoff])
        relation=lambda path:('SELECT * FROM dimension',[path])
        with patch.object(reader,'_prepared_owner',return_value=(True,None)) as full, \
                patch.object(reader,'image_metadata',side_effect=lambda _run,path:self.bound.metadata(path)), \
                patch.object(reader,'image_query',side_effect=lambda _run,path:relation(path)), \
                patch.object(subject.ExcessBinding,'query',side_effect=relation), \
                patch.object(subject.ExcessBinding,'history_query',side_effect=lambda _cutoff:(full_history[0],list(full_history[1]))), \
                patch.object(reader.connection,'cursor',return_value=cursor):
            for kind in subject.KINDS:
                for payload in ({'horison':30},{'horison':30,'supplyChainFilter':{'filters':[
                    {'attributeName':'forChildren','value':'Parent'}]},'customAttributeFilter':{'filters':[
                    {'attributeName':'skulocattr1','value':'pair','operator':'equalto'}]}}):
                    predicate=InsightPredicate(payload,[],kind=kind)
                    reader.read_prepared(self.run,cutoff,predicate,Codes(['S']),Codes(['W']),kind,payload=payload)
                    expected=cursor.execute.call_args
                    full.reset_mock()
                    reader.read_prepared(self.run,cutoff,predicate,Codes(['S']),Codes(['W']),kind,
                        payload=payload,read_binding=self.bound)
                    self.assertEqual(cursor.execute.call_args,expected)
                    full.assert_not_called()

    def test_scoped_history_response_and_horison_contract(self):
        with patch('mta.presentation.native_publication.enabled',return_value=True), \
                patch('mta.presentation.native_publication.require_mode'), \
                patch.object(subject.ExcessBinding,'attributes',return_value={'SkuAttributeData':[],'LocationAttributeData':[]}), \
                patch.object(subject.ExcessBinding,'read',return_value=[('2026-10-24',None,12)]) as read, \
                patch.object(insight_history_sql,'scope',return_value=(Codes(['S']),Codes(['W']))):
            result=insight_history_sql.read_history(self.run,{'horizon':30,'horison':2},'excess-value',read_binding=self.bound)
            self.assertEqual(result,[dict(date='2026-10-24',locationtype='-',value=12)])
            self.assertEqual(read.call_args.args[0],self.run.business_date-timedelta(days=2))
            self.assertEqual(self.history['coverage_cutoff'],'2026-10-22')
            with self.assertRaisesRegex(PublicationUnavailable,'binding_differs'):
                insight_history_sql.read_history(self.run,{},'availability-trend',read_binding=self.bound)
