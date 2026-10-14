"""Pure component proof for a proposed projection, not transition acceptance."""
from copy import deepcopy
from unittest import TestCase

from mta.mdm.location_projection import additional_owners
from mta.mdm.master_owners import business_fields
from mta.runtime.mdm_models import MdmLocationAttributes
from mta.serialization import digest, storage


class LocationProjectionTests(TestCase):
    def setUp(self):
        base={f.name:None for f in business_fields(MdmLocationAttributes)}
        active=base|dict(WHCode='ACTIVE',LocationType='DP',c4='')
        inactive=base|dict(WHCode='LP002',LocationType='LDC-LP',c4='')
        importer=dict(LocationAttributeData=[active,inactive,deepcopy(active)],
            SiteDescriptionTbl=[dict(WHCode='ACTIVE',WHDescription='Active'),
                dict(WHCode='LP002',WHDescription='Retained')])
        self.closing=dict(importer=importer,dbm=deepcopy(importer),btr=dict(
            LocationAttributeData=[active|dict(WhType='non-cwh',IsChild=True,IsParent=False)],
            SiteDescriptionTbl=[dict(WHCode='ACTIVE',WHDescription='Active')]))

    def test_complete_values_duplicates_source_order_and_btr_subset(self):
        original=deepcopy(self.closing)
        batches,proof=additional_owners(self.closing)
        self.assertEqual(len(batches),6)
        self.assertEqual(self.closing,original)
        for _,model,partition,rows,path in batches:
            owner=partition['owner'];table='LocationAttributeData' if model is MdmLocationAttributes else 'SiteDescriptionTbl'
            if owner in ('BPR','DBM'):
                self.assertEqual(storage(rows),original['importer'][table])
            elif table=='LocationAttributeData':
                self.assertEqual(storage(rows),[{k:v for k,v in original['btr'][table][0].items()
                    if k not in ('WhType','IsChild','IsParent')}])
                self.assertEqual([r['WHCode'] for r in rows],['ACTIVE'])
            else:
                self.assertEqual(rows,original['btr'][table])
        attrs=[p for p in proof['sources'] if p['owner']=='BTR' and p['model']=='MdmLocationAttributes'][0]
        self.assertEqual(attrs['derived_fields_retained_in_typed_closing'],['IsChild','IsParent','WhType'])
        self.assertEqual(attrs['source_digest'],digest(original['btr']['LocationAttributeData']))
        self.assertNotEqual(attrs['source_digest'],attrs['projected_digest'])

    def test_unknown_missing_fields_and_wrong_derived_types_are_denied(self):
        for change in ('unknown','missing','wrong_type'):
            with self.subTest(change=change):
                value=deepcopy(self.closing)
                row=value['btr']['LocationAttributeData'][0]
                if change=='unknown':row['unrepresented']='value'
                elif change=='missing':del row['IsParent']
                else:row['IsParent']=1
                with self.assertRaises(ValueError):additional_owners(value)

    def test_dbm_missing_duplicate_or_null_empty_difference_is_denied(self):
        for change in ('duplicate','null'):
            with self.subTest(change=change):
                value=deepcopy(self.closing)
                if change=='duplicate':value['dbm']['LocationAttributeData'].pop()
                else:value['dbm']['LocationAttributeData'][1]['c4']=None
                with self.assertRaises(ValueError):additional_owners(value)

    def test_empty_btr_is_explicit_and_does_not_fall_back_to_importer(self):
        self.closing['btr']=dict(LocationAttributeData=[],SiteDescriptionTbl=[])
        batches,_=additional_owners(self.closing)
        self.assertEqual([rows for _,_,partition,rows,_ in batches if partition['owner']=='BTR'],[[],[]])
