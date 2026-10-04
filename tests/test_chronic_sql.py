"""Real PostgreSQL differentials using typed VALUES; no fixture writes."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from mta.presentation import chronic_sql, insights
from mta.presentation.insight_filters import InsightPredicate
from mta.presentation.insight_response import chronic_grid_payload
from mta.presentation.permissions import PermissionCodes, permission_multiplicity
from mta.runtime.relational_state import CATALOG, PG_TYPES, db_value, quote


def row(table,**values):
    return {**{name:None for name,_ in CATALOG['tables'][table]},**values}


class ChronicAdmissionTests(unittest.TestCase):
    def test_approved_hierarchy_uses_existing_reader(self):
        with patch('mta.presentation.hierarchy.selected_manifest',return_value={'version':'retained'}):
            self.assertFalse(chronic_sql.native_fixture(object()))

    def test_invalid_hierarchy_preserves_publication_unavailable(self):
        from mta.presentation.hierarchy import HierarchyUnavailable
        with patch('mta.presentation.hierarchy.selected_manifest',side_effect=HierarchyUnavailable('changed')):
            with self.assertRaises(chronic_sql.PublicationUnavailable):
                chronic_sql.native_fixture(object())


@unittest.skipUnless(os.environ.get('VF_PORTFOLIO_POSTGRES_TESTS')=='1','requires PostgreSQL')
class ChronicSqlTests(unittest.TestCase):
    def setUp(self):
        self.run=SimpleNamespace(kind='LEGACY_UI_FIXTURE')
        self.products=PermissionCodes({'S':2,'s':1,None:1,'unmatched':1})
        self.locations=PermissionCodes({'L':3,None:1})
        self.state={
            'SkuAttributeData':[row('BTR/SkuAttributeData',SKUCode=s,Weight='10',SL1='Family')
                                for s in ('S','S','s',None)],
            'LocationAttributeData':[row('BTR/LocationAttributeData',WHCode=l,LL1='Zone',LocationType=t)
                                     for l,t in [('L','Leaf'),('L','Leaf'),(None,None),('P','Parent'),('P','Parent')]],
            'SkuLocAttributeData':[row('BTR/SkuLocAttributeData',SKUCode=s,LocCode=l,c1='pair')
                                   for s,l in [('S','L'),('S','L'),(None,None)]],
            'ChronicUnavalabilityData':[row('BTR/ChronicUnavalabilityData',SKUCode=s,WhCode=l,
                 ParentWhCode='P',RLT=2,BRAge=age,PhysicalInventoryColor=color,
                 PhysicalInventoryPen='12.500',PipelineInventoryPen=None,RationedQty=0)
                 for s,l,age,color in [('S','L',3,'Black'),('S','L',2,'Red'),('s','L',4,'Red'),
                                      (None,None,5,None),('unmatched','L',8,'Black')]],
            'SiteDescriptionTbl':[row('BTR/SiteDescriptionTbl',WHCode=l,WHDescription=d)
                                   for l,d in [('L','a'),('L','Z'),(None,None)]],
            'SKUDescriptionTbl':[row('BTR/SKUDescriptionTbl',SKUCode=s,SKUDescription=d)
                                  for s,d in [('S','a'),('S','Z'),('s','lower'),(None,None)]]}
        self.nms=[row('Importer/NMSAllItems',SKUCode=s,WhCode=l,SKUDescription=d)
                  for s,l,d in [('S','L','first'),('S','L','second'),(None,None,'null')]]
        self.images={'closing/btr/'+name:('BTR/'+name,rows) for name,rows in self.state.items()}
        self.images['closing/consumer_context/NMSAllItems']=('Importer/NMSAllItems',self.nms)
    def metadata(self,run,path):
        table,rows=self.images[path]
        return {'fields':[(n,n,'int' if k in ('int','bigint') else 'bool' if k=='bit' else
                          'float' if k in ('float','real') else 'str') for n,k in CATALOG['tables'][table]]}
    def relation(self,run,path):
        table,rows=self.images[path];fields=CATALOG['tables'][table]
        record='('+','.join(['%s::bigint']+['%s::'+PG_TYPES[k] for _,k in fields])+')'
        sql='SELECT * FROM (VALUES '+','.join([record]*len(rows))+') V('+','.join(
            quote(n) for n in ['vf_ordinal']+[n for n,_ in fields])+')'
        values=[v for i,r in enumerate(rows) for v in [i]+[db_value(r[n],k) for n,k in fields]]
        return sql,values
    def compare(self,kind,payload):
        predicate=InsightPredicate(payload,self.state['LocationAttributeData'],kind=kind)
        rows=(insights.chronic_grid(self.state,self.nms,filter_owners=True) if kind=='chronic-grid'
              else insights.joined_rows(self.state,{},kind,filter_owners=True))
        rows=predicate.select([r for r in rows for _ in range(permission_multiplicity(self.products,r['SKUCode'])*
                permission_multiplicity(self.locations,r['WHCode']))])
        expected=(chronic_grid_payload([{k:v for k,v in r.items() if not k.startswith('_')} for r in rows]) or []
                  if kind=='chronic-grid' else insights.project(rows,kind))
        with patch.object(chronic_sql,'image_query',side_effect=self.relation), \
             patch.object(chronic_sql,'image_metadata',side_effect=self.metadata), \
             patch.object(chronic_sql,'image_rows',side_effect=lambda r,p:self.images[p][1]), \
             patch('mta.presentation.hierarchy.selected_manifest',return_value=None), \
             patch.object(chronic_sql,'scope',return_value=(self.products,self.locations)):
            actual=chronic_sql.read_chronic(self.run,payload,kind)
        self.assertEqual(actual,expected)
        self.assertEqual([[(k,type(v)) for k,v in r.items()] for r in actual],
                         [[(k,type(v)) for k,v in r.items()] for r in expected])
    def test_all_grains_nulls_duplicates_order_and_permission_weights(self):
        for kind in ('chronic-grid','chronic-loc','chronic-sku'):
            with self.subTest(kind=kind):self.compare(kind,{})
    def test_filters_parent_weights_and_grid_eligibility(self):
        filters={'supplyChainFilter':{'filters':[{'attributeName':'forChildren','value':'Parent'}]},
                 'customAttributeFilter':{'filters':[{'attributeName':'skulocattr1','value':'pair','operator':'equalto'}]}}
        for kind in ('chronic-grid','chronic-loc','chronic-sku'):
            with self.subTest(kind=kind):self.compare(kind,{'filters':filters} if kind=='chronic-grid' else filters)


if __name__=='__main__':unittest.main()
