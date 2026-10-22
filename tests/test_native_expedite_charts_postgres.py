"""Native prepared Expedite chart reader/handler proof on committed facts."""
from copy import deepcopy
import inspect
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4


@unittest.skipUnless(os.environ.get('VF_NATIVE_EXPEDITE_CHART_PROOF')=='1',
                     'Explicit owned Expedite chart PostgreSQL proof required')
class NativeExpediteChartPostgresTests(unittest.TestCase):
    def test_complete_prepared_tables_wire_response_and_native_http_dispatch(self):
        from django.db import connection,transaction,DatabaseError
        from django.test import override_settings
        from mta.runtime.models import CalculationRun,PlanningExpediteChartMember
        from mta.runtime.services import read_outputs
        from mta.runtime import temporal
        from mta.presentation import expedite_charts,planning_expedite_chart_sql as prepared,views,context
        from mta.presentation.expedite_storage import read_expedite
        from mta.presentation.pick_post_storage import read_pick_post
        from mta.presentation.selective import image_rows
        from mta.serialization import digest
        self.assertEqual(connection.settings_dict['NAME'],'vf_btr_terminal_admission_20261022')
        with connection.cursor() as cursor:
            cursor.execute("SELECT oid,shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            self.assertEqual(cursor.fetchone(),(1598463,'owned terminal SMALL takeover thread01a16058 20261022; not working/serving'))
        run=CalculationRun.objects.get(pk='331a821a-853e-49c0-8f61-42c90fc6b1ce',status='SUCCEEDED')
        output=read_outputs(run);before=digest(output);headers=CalculationRun.objects.count()
        rows=read_expedite(run,output=output);pick=read_pick_post(run,output=output)
        self.assertTrue(rows);self.assertTrue(pick)
        catalogue={'version':'block1-permissions-v1'}
        for kind,table,prefix in (('products','SkuAttributeData','SL'),('locations','LocationAttributeData','LL')):
            triples={tuple(row[prefix+str(i)] for i in (1,2,3)) for row in image_rows(run,'closing/importer/'+table)}
            triples=sorted((t for t in triples if all(v is not None for v in t)),key=repr)
            records=[dict(id=i+1,**{'level_'+str(j+1):v for j,v in enumerate(t)}) for i,t in enumerate(triples)]
            records.append({**records[0],'id':10001});catalogue[kind]={'records':records}
        base=dict(category='expedite',filters={},product_permissions=[r['id'] for r in catalogue['products']['records']],
            location_permissions=[r['id'] for r in catalogue['locations']['records']])
        observations=[]
        settings=dict(VF_MTA_NATIVE_PUBLICATION=True,VF_MTA_DAILY_PUBLICATION=True,VF_MTA_SYNTHETIC_ROSTER='',
            VF_MTA_FIXTURE_FILE='',VF_MTA_FIXTURE_SHA256='',VF_MTA_OPERATIONAL_POLICY='',
            VF_MTA_OPERATIONAL_RECEIPT='',VF_MTA_CONSUMPTION_POLICY='',
            VF_MTA_HIERARCHY_FILE='',VF_MTA_HIERARCHY_SHA256='')
        with override_settings(**settings),patch.object(context,'permission_catalogue',return_value=catalogue), \
                patch('mta.presentation.planning_expedite_transit_preparation.pick_source',
                    side_effect=AssertionError('No fixture Pick source')), \
                patch.object(temporal,'execute_day',side_effect=AssertionError('No daily execution')), \
                patch.object(temporal,'calculate_day',side_effect=AssertionError('No calculation')):
            importer=output['ClosingState'][0]['importer']
            for name,scope_payload in (('all',base),('denied',{**base,'product_permissions':[]}),
                ('single-permission',{**base,'product_permissions':[1],'location_permissions':[1]})):
                for direction in ('parent','child'):
                    payload={**scope_payload,'type':direction}
                    products,locations=context.scope(payload,attributes=importer)
                    expected=expedite_charts.queries(output,rows,pick,direction,products=products,locations=locations)
                    actual=prepared.queries(run,payload,direction)
                    self.assertEqual(actual,expected,(name,direction))
                    self.assertEqual(digest(actual),digest(expected))
                    wire=expedite_charts.response(expected,direction,receiving_own_label=True)
                    with patch.object(views,'selected_run',return_value=run), \
                            patch.object(prepared,'queries',wraps=prepared.queries) as dispatch, \
                            patch('mta.presentation.expedite_read.expedite_context',
                                side_effect=AssertionError('No broad chart reconstruction')):
                        response=inspect.unwrap(views.planning_graph)(None,payload)
                    dispatch.assert_called_once_with(run,payload,direction)
                    self.assertEqual(json.loads(response.content)['data'],wire)
                    observations.append(dict(scope=name,direction=direction,
                        populations={k:len(v) for k,v in actual.items()},digest=digest(actual),wire_digest=digest(wire)))
            foreign=deepcopy(run);foreign.pk=uuid4()
            with self.assertRaises(ValueError):prepared.queries(foreign,base,'parent')
            with self.assertRaises(ValueError):prepared.queries(run,base,'unsupported')
            with self.assertRaises(ValueError):prepared.queries(run,{**base,'product_permissions':[999999]},'parent')
            with transaction.atomic():
                with self.assertRaises(DatabaseError),transaction.atomic():
                    PlanningExpediteChartMember.objects.filter(run=run).update(code='tampered')
                transaction.set_rollback(True)
        self.assertEqual(CalculationRun.objects.count(),headers);self.assertEqual(digest(read_outputs(run)),before)
        print('NATIVE_EXPEDITE_CHART_PASS '+json.dumps(observations,sort_keys=True))
