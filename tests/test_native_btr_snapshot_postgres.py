"""Native BTR display qualification over already committed owned fixture facts."""
from copy import copy,deepcopy
from datetime import timedelta
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4


@unittest.skipUnless(os.environ.get('VF_NATIVE_BTR_SNAPSHOT_PROOF')=='1',
                     'Explicit owned native BTR PostgreSQL proof required')
class NativeBtrSnapshotPostgresTests(unittest.TestCase):
    def test_native_builder_full_readers_counts_exports_guards_and_rollback(self):
        from django.db import connection,transaction,DatabaseError
        from django.test import override_settings
        from mta.runtime.models import CalculationRun,BtrReportingGeneration,BtrPresentationRow
        from mta.runtime import temporal
        from mta.runtime.services import read_outputs
        from mta.presentation import btr_snapshot,btr_reporting,btr_sql,btr_display,context,daily_preparation
        from mta.presentation.selective import image_rows
        from mta.serialization import digest
        self.assertEqual(connection.settings_dict['NAME'],'vf_btr_terminal_admission_20261022')
        with connection.cursor() as cursor:
            cursor.execute("SELECT oid,shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            self.assertEqual(cursor.fetchone(),(1598463,'owned terminal SMALL takeover thread01a16058 20261022; not working/serving'))
        run=CalculationRun.objects.get(pk='331a821a-853e-49c0-8f61-42c90fc6b1ce',status='SUCCEEDED')
        before=digest(read_outputs(run));headers=CalculationRun.objects.count()
        generations=BtrReportingGeneration.objects.count();display_rows=BtrPresentationRow.objects.count()
        settings=dict(VF_MTA_PUBLISHED_RUN='',VF_MTA_HIERARCHY_FILE='',VF_MTA_HIERARCHY_SHA256='',
            VF_MTA_NATIVE_PUBLICATION=True,VF_MTA_DAILY_PUBLICATION=True,VF_MTA_SYNTHETIC_ROSTER='',
            VF_MTA_FIXTURE_FILE='',VF_MTA_FIXTURE_SHA256='',VF_MTA_OPERATIONAL_POLICY='',
            VF_MTA_OPERATIONAL_RECEIPT='',VF_MTA_CONSUMPTION_POLICY='')
        with override_settings(**settings),transaction.atomic(), \
                patch.object(temporal,'execute_day',side_effect=AssertionError('No daily execution')), \
                patch.object(temporal,'calculate_day',side_effect=AssertionError('No calculation')), \
                patch('mta.presentation.admission.binding',side_effect=AssertionError('No serving admission')):
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.daily_publication_build',%s,true)",[str(run.pk)])
            reference=btr_reporting.build_run(run)
            self.assertTrue(reference.eligible);self.assertEqual(reference.version,1)
            receipt=daily_preparation._btr_result(run,verify_only=False)
            generation=BtrReportingGeneration.objects.get(pk=receipt['generation'])
            self.assertEqual(generation.version,2)
            self.assertEqual(generation.row_count,reference.qualification['populations']['tech_grid']+
                             reference.qualification['populations']['eco_grid'])
            self.assertEqual(daily_preparation._btr_result(run,verify_only=True,
                generation_id=str(generation.pk)),receipt)
            self.assertEqual(btr_snapshot.build_run(run,reference).pk,generation.pk)
            self.assertEqual(btr_snapshot.reference_generation(run,generation).pk,reference.pk)
            catalogue={'version':'block1-permissions-v1'}
            for name,path,prefix in (('products','SkuAttributeData','SL'),('locations','LocationAttributeData','LL')):
                triples=sorted({tuple(row[prefix+str(i)] for i in (1,2,3))
                    for row in image_rows(run,'closing/btr/'+path)},key=repr)
                # Retain native NULL hierarchies in storage; they must never
                # be admitted by NULL-equality in the permission join.
                triples=[t for t in triples if all(v is not None for v in t)]
                self.assertTrue(triples)
                records=[dict(id=i+1,**{'level_'+str(j+1):v for j,v in enumerate(t)})
                    for i,t in enumerate(triples)]
                # Explicit test permission overlap against unchanged producer
                # attributes; actual membership expansion retains multiplicity.
                records.append({**records[0],'id':10001})
                records.append(dict(id=10002,level_1=None,level_2=None,level_3=None))
                catalogue[name]={'records':records}
            base=dict(name='both',product_permissions=[r['id'] for r in catalogue['products']['records'] if r['id']<10000],
                location_permissions=[r['id'] for r in catalogue['locations']['records'] if r['id']<10000],
                displayPrepared=True,displayHorizon=90)
            cases=[('all',base,(1,50)),('second-page',base,(2,3)),('first-page',base,(1,3)),
                ('short-horizon',{**base,'displayHorizon':7},(1,50)),
                ('date-window',{**base,'displayHorizon':7,'filters':{'horizonFilter':{'filters':[
                    {'attributeName':'startDate','value':str(run.business_date-timedelta(days=6))},
                    {'attributeName':'endDate','value':str(run.business_date)}]}}},(1,50)),
                ('denied',{**base,'product_permissions':[]},(1,50)),
                ('null-denied',{**base,'product_permissions':[10002]},(1,50)),
                ('overlap',{**base,'product_permissions':base['product_permissions']+[10001],
                            'location_permissions':base['location_permissions']+[10001]},(1,50)),
                ('sku-filter',{**base,'filters':{'productFilter':{'filters':[
                    {'attributeName':'sku','operator':'equalto','value':'5954'}]}}},(1,50)),
                ('null-filter',{**base,'filters':{'customAttributeFilter':{'filters':[
                    {'attributeName':'SKUAttr15','operator':'hasnovalue','value':''}]}}},(1,50))]
            observations=[]
            with patch.object(context,'permission_catalogue',return_value=catalogue):
                for name,payload,paging in cases:
                    with override_settings(VF_BTR_REPORTING_GENERATION=str(reference.pk)):
                        expected=btr_display.prepare_display(btr_sql.read_btr(run,deepcopy(payload),paging=paging),
                            payload['displayHorizon'])
                        counts=btr_sql.read_btr(run,payload,paging=paging,count=True)
                    with override_settings(VF_BTR_REPORTING_GENERATION=str(generation.pk)):
                        with patch.object(btr_snapshot,'read_snapshot',wraps=btr_snapshot.read_snapshot) as dispatch:
                            actual=btr_sql.read_btr(run,payload,paging=paging)
                        dispatch.assert_called_once()
                        self.assertEqual(actual,expected,name)
                        self.assertEqual(digest(actual),digest(expected),name)
                        self.assertEqual(btr_sql.read_btr(run,payload,paging=paging,count=True),counts,name)
                    if name=='all':self.assertTrue(actual['tech']);self.assertTrue(actual['eco'])
                    observations.append(dict(case=name,rows={b:len(actual[b]) for b in ('tech','eco')},
                        digest=digest(actual),counts=counts))
                for branch in ('tech','eco'):
                    payload={**base,'name':branch}
                    exports=[]
                    for selected in (reference,generation):
                        with override_settings(VF_BTR_REPORTING_GENERATION=str(selected.pk)):
                            rows,labels=btr_sql.read_btr(run,payload,paging=None,export=True)
                            exports.append((list(rows),labels))
                    self.assertEqual(exports[0],exports[1]);self.assertTrue(exports[0][0])
                for selected in (reference,generation):
                    with override_settings(VF_BTR_REPORTING_GENERATION=str(selected.pk)), \
                            self.assertRaisesRegex(context.PublicationUnavailable,'permission_hierarchy_unavailable'):
                        btr_sql.read_btr(run,{**base,'product_permissions':[99999]},paging=(1,50))
            for change in ({'run_id':uuid4()},{'source_digest':'0'*64}):
                foreign=copy(reference)
                for field,value in change.items():setattr(foreign,field,value)
                with self.assertRaisesRegex(context.PublicationUnavailable,'qualified_reference'):
                    btr_snapshot.build_run(run,foreign)
            with override_settings(VF_MTA_PUBLISHED_RUN=str(run.pk)), \
                    self.assertRaisesRegex(context.PublicationUnavailable,'unselected_committed'):
                btr_snapshot.build_run(run,reference)
            with self.assertRaises(DatabaseError),transaction.atomic():
                BtrPresentationRow.objects.filter(generation=generation).update(branch='eco')
            ambiguous=copy(reference);ambiguous.eligible=False
            with patch.object(btr_reporting,'build_run',return_value=ambiguous), \
                    patch.object(btr_snapshot,'build_run',side_effect=AssertionError('No ambiguous display build')):
                fallback=daily_preparation._btr_result(run,verify_only=False)
            self.assertEqual(fallback['generation'],str(reference.pk))
            self.assertEqual(fallback['display_fallback'],'normalized_source_ambiguity')
            transaction.set_rollback(True)
        self.assertEqual(BtrReportingGeneration.objects.count(),generations)
        self.assertEqual(BtrPresentationRow.objects.count(),display_rows)
        self.assertEqual(CalculationRun.objects.count(),headers)
        self.assertEqual(digest(read_outputs(run)),before)
        print('NATIVE_BTR_DISPLAY_PASS '+json.dumps(dict(cases=observations,
            counts_exports_reference=True,foreign_source_denied=True,sealed_mutation_denied=True,
            operational_values_unchanged=True,rollback=True),sort_keys=True))
