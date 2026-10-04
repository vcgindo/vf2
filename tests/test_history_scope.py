"""Selected producer scope preserves the full-image membership decision."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
os.environ.setdefault('VF_SECRET_KEY','unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.presentation import context, fixture

class HistoryScopeTest(unittest.TestCase):
    def test_selected_rows_preserve_full_scope_memberships_and_errors(self):
        records=[dict(id=1,level_1='Parent ',level_2=None,level_3=None),
                 dict(id=2,level_1='PARENT',level_2=' Branch ',level_3='LEAF'),
                 dict(id=3,level_1='Other',level_2='Branch',level_3='Leaf')]
        catalogue={kind:{'records':records} for kind in ('products','locations')}
        sku=[dict(SKUCode=code,SL1=a,SL2=b,SL3=c) for code,a,b,c in [
            ('sku',' parent ','branch','leaf'),('sku','parent',' BRANCH ','Leaf'),
            ('SKU','parent','branch','leaf'),('sku ','parent','branch','leaf'),
            ('missing','parent',None,'leaf'),('other','Other','Branch','Leaf')]]
        loc=[dict(WHCode=code,LL1=a,LL2=b,LL3=c) for code,a,b,c in [
            ('loc','parent','branch','leaf'),('loc','parent','branch','leaf'),
            ('LOC','parent','branch','leaf'),('missing',None,'branch','leaf')]]
        full={'SkuAttributeData':sku,'LocationAttributeData':loc}
        with patch.object(context,'permission_catalogue',return_value=catalogue):
            for pair in [('sku','loc'),('SKU','LOC'),('sku ','loc'),('missing','missing'),('absent','loc')]:
                small={'SkuAttributeData':[r for r in sku if r['SKUCode']==pair[0]],
                       'LocationAttributeData':[r for r in loc if r['WHCode']==pair[1]]}
                for ids in ([1],[2],[3],[],['1','2'],[True],['bad'],[999]):
                    payload={'product_permissions':ids,'location_permissions':ids}
                    if any(isinstance(v,bool) or str(v) in ('bad','999') for v in ids):
                        errors=[]
                        for attrs in (full,small):
                            with self.assertRaises(ValueError) as raised:context.scope(payload,attributes=attrs)
                            errors.append((type(raised.exception),str(raised.exception)))
                        self.assertEqual(*errors)
                    else:
                        expected=context.scope(payload,attributes=full)
                        actual=context.scope(payload,attributes=small)
                        for code,old,new in zip(pair,expected,actual):
                            self.assertEqual(code in old,code in new)
                            self.assertEqual(old.multiplicities[code],new.multiplicities[code])
            products,locations=context.scope({'product_permissions':[1],'location_permissions':[1]},attributes=full)
            self.assertEqual(products.multiplicities['sku'],2)
            self.assertEqual(locations.multiplicities['loc'],2)
            self.assertNotIn('missing',products)

    def test_read_is_bound_to_named_run_image_exact_code_and_four_fields(self):
        path='closing/importer/SkuAttributeData'
        fields=[[name,name,'str'] for name in ('SKUCode','SL1','SL2','SL3','Other')]
        metadata={'image':path,'fields':fields,'table':'Importer/SkuAttributeData'}
        cursor=MagicMock();cursor.fetchall.return_value=[('sku','Root','Branch',None)]*2
        with patch.object(fixture,'_validate_image_metadata',return_value=metadata),patch.object(fixture.connection,'cursor') as db:
            db.return_value.__enter__.return_value=cursor
            rows=fixture.history_scope_rows(SimpleNamespace(pk='chosen-run'),path,'sku',metadata=metadata)
        sql,params=cursor.execute.call_args.args
        self.assertEqual(params,['chosen-run',path,'sku'])
        self.assertIn('"SKUCode"=%s ORDER BY vf_ordinal',sql)
        self.assertNotIn('Other',sql)
        self.assertNotIn('lower(',sql)
        self.assertEqual(rows,[dict(SKUCode='sku',SL1='Root',SL2='Branch',SL3=None)]*2)

    def test_wrong_image_or_missing_permission_fields_fail_closed(self):
        with self.assertRaisesRegex(context.PublicationUnavailable,'history_scope_outside_boundary'):
            fixture.history_scope_rows(None,'closing/dbm/DBMMaster','sku',metadata={})
        path='closing/importer/SkuAttributeData'
        with patch.object(fixture,'_validate_image_metadata',return_value={'fields':[]}),patch.object(fixture.connection,'cursor') as db:
            with self.assertRaisesRegex(context.PublicationUnavailable,'history_scope_columns_changed'):
                fixture.history_scope_rows(None,path,'sku',metadata={})
            db.assert_not_called()

