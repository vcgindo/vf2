"""GIT consumers over real accepted scoped inputs; rollback-only components."""
from dataclasses import replace
from copy import deepcopy
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_transit_storage_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedGitTests(unittest.TestCase):
    for _name in ('setUp','rollback','accept','bpr','positive'):
        locals()[_name]=fixtures.ScopeTransitStorageTests.__dict__[_name]

    def owner(self,**options):
        from tests import production_h3_fixture as h3
        original=h3.supplied_day
        def day(*args,**kwargs):
            value=original(*args,**kwargs)
            for row in value['day']['raw_daily']:
                if (row['SKUCode'],row['WhCode'])==('SUPPLIED-Z9',h3.CHILD):
                    # Explicit first-known external zero-stock boundary. No
                    # receipt/consumption or prior calculated stock is seeded.
                    row.update(Stock=0,Consumption=0,Receipts=0)
            return value
        with patch.object(h3,'supplied_day',side_effect=day):
            fixtures.ScopeTransitStorageTests.owner(self,**options)

    def parents(self,*,empty=False,counter=False):
        from mta.presentation import scoped_report_storage as facts,scoped_prepared,scoped_transit_storage
        self.positive(duplicates=True)
        if empty:
            self.transit_sources['shipments']['rows']=[]
            self.transit_sources['transporters']['rows']=[]
        self.bpr(counter=counter)
        self.transit=scoped_transit_storage.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        self.report=facts.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        self.prepared=scoped_prepared.prepare(self.report.pk,expected_report_digest=self.report.digest,action_revision=0)
        self.bound=scoped_prepared.bind(self.report.pk,expected_digest=self.prepared.digest,
            expected_report_digest=self.report.digest,action_revision=0,include_nms=True,
            transit_generation_id=self.transit.pk,expected_transit_digest=self.transit.digest)

    def scopes(self):
        from mta.presentation.permissions import PermissionCodes
        return (PermissionCodes({'SUPPLIED-Z9':2}),
            PermissionCodes({'OWN-WH8':3,'OWN-PARENT':3}))

    def occurrences(self,bound=None):
        from mta.presentation.planning_git_preparation import production_git_occurrences
        from django.db import connection
        query,params=production_git_occurrences(self.run,read_binding=bound or self.bound)
        with connection.cursor() as cursor:
            cursor.execute(query,params);names=[c[0] for c in cursor.description]
            return [dict(zip(names,r)) for r in cursor.fetchall()]

    def target(self,rows):
        keys={(r['rationed_ordinal'],r['standard_ordinal']) for r in self.bound.rows('git_master')
            if (r['SKUCode'],r['WhCode'])==('SUPPLIED-Z9','OWN-WH8')}
        return [r for r in rows if (r['rationed_ordinal'],r['standard_ordinal']) in keys]

    def test_actual_occurrence_source_preserves_transporter_ordinals_and_default_sql(self):
        from mta.presentation import planning_git_preparation as producer
        self.parents();rows=self.target(self.occurrences())
        self.assertEqual(len(rows),4)
        self.assertEqual(sorted(r['transporter_ordinal'] for r in rows),[0,1,2,3])
        self.assertTrue(all(r['grid_eligible'] for r in rows))
        self.assertTrue(all(r['parent_description'] is not None for r in rows))
        relations=dict(git_master=self.bound.query('git_master'))
        query,params=producer.production_git_occurrences(self.run,read_binding=self.bound)
        with patch.object(producer,'admitted_sources',return_value=relations), \
                patch.object(producer,'image_query',side_effect=lambda run,path:self.bound.image_query(path)):
            default,default_params=producer.production_git_occurrences(self.run)
        self.assertEqual(query.replace(',tm.vf_ordinal AS "transporter_ordinal"',''),default)
        self.assertEqual(params,default_params)

    def test_complete_graph_matches_independent_existing_dataset_builder(self):
        from mta.presentation import daily_git_read as reader,daily_git_charts as pure,daily_git_preparation as source
        self.parents();products,locations=self.scopes()
        inputs=dict(transporter=self.bound.transit.rows('GoodsInTransitTransporterMaster'),
            transit=self.bound.transit.rows('InTransitData'),git_master=self.bound.rows('git_master'),
            location_attributes=self.bound.sources.rows(source.LOCATION_PATH),
            location_descriptions=self.bound.sources.rows(source.DESCRIPTION_PATH),
            product_scope=products,location_scope=locations,dynamic_attributes=[],dynamic_ui_config=[])
        expected=pure.build(**inputs)
        datasets=pure.datasets(**inputs)
        self.assertEqual(sum(r['counts'] for r in datasets['tables'][2]),24)
        self.assertEqual(datasets['tables'][1],[]);self.assertEqual(datasets['tables'][3],[])
        # NULL pre-BTR SLT is preserved; no delayed status is invented.
        with patch.object(source,'image_metadata',side_effect=AssertionError('terminal metadata')), \
                patch.object(source,'image_query',side_effect=AssertionError('terminal source')):
            actual=reader.graph(self.run,products,locations,read_binding=self.bound)
        self.assertEqual(actual,expected)
        relations,bindings,config=source.sources(self.run,chart=True,read_binding=self.bound)
        with patch.object(reader,'sources',return_value=(relations,bindings,config)):
            self.assertEqual(reader.graph(self.run,products,locations),expected)

    def test_custom_complete_bag_paging_null_omission_and_native_unequal_tie_denial(self):
        from mta.presentation import daily_git_custom as reader,daily_git_preparation as source
        from mta.presentation.context import PublicationUnavailable
        from django.db import transaction
        self.parents();products,locations=self.scopes()
        actual=reader.custom(self.run,products,locations,None,read_binding=self.bound)
        self.assertEqual(len(actual['data']),48)
        self.assertEqual([r['RN'] for r in actual['data']],list(range(1,49)))
        self.assertTrue(all((r['sc'],r['wc'],r['itq'],r['lc'])==('SUPPLIED-Z9','OWN-WH8',4,'L-1')
            for r in actual['data']))
        self.assertTrue(all('dd' not in r and 'slt' not in r and 'eta' not in r and 'rmk' not in r
            and 'tct' not in r for r in actual['data']))
        relations,bindings,config=source.sources(self.run,chart=False,read_binding=self.bound)
        with patch.object(reader,'sources',return_value=(relations,bindings,config)):
            self.assertEqual(reader.custom(self.run,products,locations,None),actual)
        paged=reader.custom(self.run,products,locations,(2,5),read_binding=self.bound)
        self.assertEqual(paged,dict(data=actual['data'][5:10],uiConfig=actual['uiConfig']))
        with transaction.atomic():
            # parents() constructs its fixture; retain this explicit directory
            # delta by changing positive() only during new source construction.
            original=self.positive
            def distinct(**kwargs):
                original(**kwargs)
                self.transit_sources['transporters']['rows'][1]=deepcopy(self.transit_sources['transporters']['rows'][1])
                self.transit_sources['transporters']['rows'][1]['TransporterName']='Different declared carrier'
            with patch.object(self,'positive',side_effect=distinct):self.parents()
            with self.assertRaisesRegex(PublicationUnavailable,'UNORDERED-TIE'):
                reader.custom(self.run,products,locations,None,read_binding=self.bound)
            transaction.set_rollback(True)

    def test_transporter_count_grouping_directional_permissions_and_invalid_filter(self):
        from mta.presentation.daily_git_count import count
        from mta.presentation.permissions import PermissionCodes
        from mta.presentation.context import PublicationUnavailable
        self.parents();products,locations=self.scopes()
        self.assertEqual(count(self.run,{},products,locations,read_binding=self.bound),1)
        self.assertEqual(count(self.run,{},products,PermissionCodes({'OWN-WH8':3}),read_binding=self.bound),0)
        self.assertEqual(count(self.run,{},products,PermissionCodes({'OWN-PARENT':1}),read_binding=self.bound),1)
        payload={'filters':{'productFilter':{'filters':[dict(attributeName='p1',operator='equalto',value='C')]}}}
        with self.assertRaises(PublicationUnavailable):count(self.run,payload,products,locations,read_binding=self.bound)

    def test_missing_transit_nms_wrong_run_and_dynamic_config_deny_without_fallback(self):
        from mta.presentation import daily_git_preparation as source,daily_git_custom,daily_git_read,daily_git_count,scoped_prepared
        from mta.presentation.context import PublicationUnavailable
        self.parents();products,locations=self.scopes()
        no_transit=replace(self.bound,transit=None)
        for invoke in (lambda:source.sources(self.run,chart=True,read_binding=no_transit),
                lambda:daily_git_count.count(self.run,{},products,locations,read_binding=no_transit)):
            with self.assertRaises(PublicationUnavailable):invoke()
        no_nms=scoped_prepared.bind(self.report.pk,expected_digest=self.prepared.digest,
            expected_report_digest=self.report.digest,action_revision=0,
            transit_generation_id=self.transit.pk,expected_transit_digest=self.transit.digest)
        with self.assertRaises(PublicationUnavailable):
            daily_git_custom.custom(self.run,products,locations,None,read_binding=no_nms)
        self.assertEqual(daily_git_read.graph(self.run,products,locations,read_binding=no_nms),
            daily_git_read.graph(self.run,products,locations,read_binding=self.bound))
        visible=dict(ReportName='AdminBPR',Col_Code='LocAttr16',Header='Invalid external column',Visible=True)
        with patch.object(source,'BPR_UI_CONFIG',[visible]),self.assertRaisesRegex(PublicationUnavailable,'configuration_invalid'):
            source.sources(self.run,chart=True,read_binding=self.bound)
        original=self.bound;self.parents()
        with self.assertRaisesRegex(PublicationUnavailable,'phase_owner_differs'):
            daily_git_read.graph(self.run,products,locations,read_binding=original)

    def test_explicit_empty_sources_and_empty_permissions_settle_without_write(self):
        from mta.presentation import daily_git_custom,daily_git_read,daily_git_count
        from mta.presentation.permissions import PermissionCodes
        from mta.runtime.scope_revisions import require_current
        self.parents(empty=True,counter=True);before=require_current(self.run)
        products,locations=self.scopes()
        for p,l in ((products,locations),(PermissionCodes({}),locations)):
            self.assertEqual(daily_git_custom.custom(self.run,p,l,None,read_binding=self.bound)['data'],[])
            self.assertEqual(daily_git_count.count(self.run,{},p,l,read_binding=self.bound),0)
            self.assertEqual(daily_git_read.graph(self.run,p,l,read_binding=self.bound),
                self.empty_graph())
        rows=self.target(self.occurrences())
        self.assertEqual(len(rows),1);self.assertIsNone(rows[0]['transporter_ordinal'])
        self.assertEqual(require_current(self.run),before)

    @staticmethod
    def empty_graph():
        from mta.presentation.daily_git_charts import response,BASE_CONFIG
        return response(dict(tables=[[],[],[],[]],ui_config=BASE_CONFIG))
