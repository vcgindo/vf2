"""Actual typed input roundtrips; no execute_day or business calculation."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import unittest

from django.db import connection, transaction
from mta.runtime.input_storage import save_input, read_input, choose_table
from mta.runtime.models import CalculationRun
from mta.runtime.daily_bindings import apply_pick, apply_finalization
from mta.serialization import digest


class VehicleInputStorageTests(unittest.TestCase):
    def setUp(self):
        self.atomic = transaction.atomic()
        self.atomic.__enter__()
        self.addCleanup(self.rollback)

    def rollback(self):
        transaction.set_rollback(True)
        self.atomic.__exit__(None, None, None)

    def roundtrip(self, raw, text):
        run = CalculationRun.objects.create(input_digest=digest(raw),
            execution_revision='vehicle-representation-fixture',
            business_date='2026-06-06', kind='INPUT_FIXTURE', input_payload={})
        run.input_payload = save_input(run, raw)
        run.input_manifest_digest = digest(run.input_payload)
        run.save()
        run.refresh_from_db()
        self.assertEqual(read_input(run), raw)
        self.assertEqual(digest(read_input(run)), run.input_digest)
        for plural, singular in [('vehicles','vehicle'), ('location_vehicles','location_vehicle')]:
            path='input/profile/calculation/logistics/'+plural+'/values'
            image=run.input_payload['images'][path]
            self.assertEqual(image['table'],'input/'+singular+('_text' if text else ''))
        return run

    def raw(self, identity):
        vehicle=dict(vehicle_id=identity, name='Truck ', weight_capacity=1000, volume_capacity=1200)
        location=dict(location_code='LDC001', vehicle_id=identity)
        return dict(profile=dict(delivery=dict(site_code='VECTORFLOW-DEMO'),
            calculation=dict(logistics=dict(
                vehicles=[vehicle,deepcopy(vehicle),{k:None for k in vehicle}],
                location_vehicles=[location,deepcopy(location),{k:None for k in location}]))))

    def test_text_duplicates_nulls_and_lexical_identity(self):
        for identity in ('DEMO-TRUCK','00017','Truck Ω '):
            with self.subTest(identity=identity):
                run=self.roundtrip(self.raw(identity),True)
                self.assertNotIn(identity,str(run.input_payload))

    def test_numeric_and_null_families_keep_original_tables(self):
        for identity in (17,2147483649,None):
            with self.subTest(identity=identity):self.roundtrip(self.raw(identity),False)

    def test_text_family_does_not_change_generic_table_selection(self):
        fields=self.raw(17)['profile']['calculation']['logistics']['vehicles'][0]
        self.assertEqual(choose_table(fields,'input/elsewhere/values', [fields]),'input/vehicle')

    def test_exact_approved_frozen_profile_and_opening(self):
        root=Path(os.environ['VF_COHORT6_INPUT_PROOF_ROOT'])
        def bound(name, expected):
            data=(root/name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),expected)
            return data
        artifact_sha='7ee7d940da3bab89ffeeddff94b4f2a7d9abace4aacdd589d698df6de85c24fc'
        artifact=json.loads(bound('input.json',artifact_sha))
        final_sha='9a646e0eb3b455e495be3a6abb3cc11854594962def6171571bac5e834fef1b1'
        final=bound('finalization.json',final_sha)
        pick=bound('pick.json','a775176974652ae0c228ab70a11ef4a5cbc2447b6535929397e914cc0e4b1c51')
        case=artifact['case']
        profile,opening=apply_finalization(case['profile'],case['opening'],final,
            artifact_sha256=artifact_sha,config_sha256=final_sha,business_date='2026-06-06')
        profile=apply_pick(profile,pick,'canonical-tied-order-v1')
        raw=dict(profile=profile,opening=dict(state=opening),
                 day={**deepcopy(case['days'][0]),**deepcopy(case['static_day'])})
        self.roundtrip(raw,True)

    def test_physical_column_types(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT table_name,data_type FROM information_schema.columns WHERE table_schema='mta_state' AND column_name='vehicle_id' AND table_name IN ('input_vehicle','input_location_vehicle','input_vehicle_text','input_location_vehicle_text')")
            self.assertEqual(dict(cursor.fetchall()),dict(input_vehicle='bigint',
                input_location_vehicle='bigint',input_vehicle_text='text',input_location_vehicle_text='text'))
