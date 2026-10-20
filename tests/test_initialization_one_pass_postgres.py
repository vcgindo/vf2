"""One disposable migrated database proves the changed initialization boundary.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
if not os.environ.get('VF_SECRET_KEY_FILE'):
    os.environ.setdefault('VF_SECRET_KEY','m2-focused-proof')
import django
django.setup()
from django.db import connection, transaction


@unittest.skipUnless(os.environ.get('VF_INGESTION_M2_POSTGRES_PROOF')=='1','Explicit disposable M2 database required')
class OnePassPostgresTests(unittest.TestCase):
    def test_csv_registration_atomic_families_certification_and_resume(self):
        from release import initialize_csv as driver, register_mta
        from mta.application.initialization_csv import create, MANIFEST
        from mta.mdm import initialization as init, production_families as families
        from mta.runtime import opening_storage, ingestion_certification as certification
        from mta.runtime.models import ProductionInitialization, MdmSource, CalculationRun
        from mta.runtime.mdm_models import MdmFamilySource
        from mta.runtime.ingestion_models import InitializationCertification
        from tests.initialization_input_fixture import supplied_input,encoded
        from mta.serialization import digest
        from mta.runtime.input_v3 import V3
        if connection.settings_dict['NAME']!='vf_ingestion_m2_20261021':
            raise RuntimeError('Exact disposable M2 database required')
        value=supplied_input()
        value['opening']['state']['importer_settings'] += [
            dict(Parameter='NMSMOQInputDataFormat',Value='WithDestLoc'),
            dict(Parameter='ActivateNMSUIUploadLogs',Value='0')]
        # Retain equal settings copies, making one declared physical alias.
        from copy import deepcopy
        value['opening']['state']['controls']['importer_settings']=deepcopy(value['opening']['state']['importer_settings'])
        raw,sha,args=encoded(value)
        expected=__import__('mta.mdm.initialization_contract',fromlist=['decode']).decode(raw,sha,**args)[1]
        release=dict(schema='vectorflow-native-release-source-v1',source_commit='4'*40,
            manifest_sha256='5'*64,implementation_sha256=init.current_implementation_digest(),
            source_files_digest='6'*64,migrations_digest='7'*64)
        render=register_mta.render_sql
        def local_sql(text,values):
            return render(text.replace('GRANT :"owner_role", fresh_operational_acceptor TO :"issuer_role";',''),values)
        with tempfile.TemporaryDirectory() as td, patch('release.native_identity.require_current',return_value=release), \
                patch.object(register_mta,'render_sql',side_effect=local_sql), \
                patch.dict(os.environ,MTA_DB_NAME=connection.settings_dict['NAME'],
                    MTA_INSTALLER_PASSWORD_FILE='/run/secrets/mta_installer_password',
                    VF_NATIVE_RELEASE_COMMIT=release['source_commit'],VF_NATIVE_RELEASE_SHA256=release['manifest_sha256']):
            root=Path(td);(root/'binding-template.json').write_text('{}');(root/'permissions.json').write_text('{}')
            manifest,csv_raw=create(value,root/'opening')
            pin=hashlib.sha256((root/'opening'/MANIFEST).read_bytes()).hexdigest()
            receipt=root/'onboarding.json'
            initial_receipt=dict(status='VALIDATING',phase='CSV',manifest_sha256=pin,
                pack_pins={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
                    for name in ('binding-template.json','permissions.json')})
            with connection.cursor() as cursor:
                cursor.execute("SELECT to_regclass('fresh_control.application_capability')")
                registered=cursor.fetchone()[0] is not None
            if registered:
                # Reuse only this empty same-source proof checkpoint after a
                # test assertion fault, never erase/recreate business rows.
                self.assertEqual(ProductionInitialization.objects.count(),0)
                self.assertEqual(InitializationCertification.objects.count(),0)
                initial_receipt['registration']=driver.registered_checkpoint(manifest['native_input_sha256'])
                initial_receipt['phase']='INITIALIZATION'
            driver.write_receipt(receipt,initial_receipt)
            call=lambda resume: driver.run(root,pin,args['expected_configuration'],args['expected_recipe'],receipt,resume=resume)
            original_install=families._install
            calls=[]
            def broken_family(*a):
                result=original_install(*a);calls.append(a[1])
                raise ValueError('M2 injected family failure')
            with patch.object(families,'_install',side_effect=broken_family),self.assertRaisesRegex(ValueError,'injected family'):
                call(registered)
            self.assertEqual(calls,['supplier'])
            self.assertEqual((ProductionInitialization.objects.count(),MdmSource.objects.count(),MdmFamilySource.objects.count()),(0,0,0))
            self.assertIn('registration',json.loads(receipt.read_text()))
            self.assertNotIn('initialization',json.loads(receipt.read_text()))
            # The registration commit can precede its receipt write. Recover
            # that exact namespace, never register it again.
            checkpoint=json.loads(receipt.read_text())
            checkpoint.pop('registration');checkpoint['phase']='REGISTRATION'
            driver.write_receipt(receipt,checkpoint)
            actual_certify=certification.certify_locked
            def broken_certify(*a):
                actual_certify(*a)
                raise ValueError('M2 injected final audit failure')
            with patch.object(certification,'certify_locked',side_effect=broken_certify), \
                    patch.object(register_mta,'register',side_effect=AssertionError('Repeated registration')), \
                    self.assertRaisesRegex(ValueError,'injected final audit'):
                call(True)
            self.assertEqual((ProductionInitialization.objects.count(),InitializationCertification.objects.count(),MdmFamilySource.objects.count()),(0,0,0))
            # A supported base-only current-release checkpoint can finish its
            # family roster without another initialization. Keep this compact
            # compatibility scenario rolled back in the same disposable DB.
            from mta.runtime.opening_scope import opening_scope
            with driver.installer_login(),opening_scope(),transaction.atomic():
                owner,created=init.initialize(csv_raw,manifest['native_input_sha256'],**args)
                self.assertTrue(created)
                identity=owner.pk
                with patch.object(init,'initialize',side_effect=AssertionError('Initialization replay')):
                    init._complete(owner,init.read_initialized_input(owner))
                self.assertEqual(InitializationCertification.objects.get().initialization_id,identity)
                transaction.set_rollback(True)
            self.assertEqual(ProductionInitialization.objects.count(),0)
            # One complete successful SQL transaction, then a separate failed
            # activation boundary: masters/certification must not be loaded twice.
            images=[]
            actual_read=opening_storage.load_image
            def observe(owner,meta):
                images.append(meta['image']);return actual_read(owner,meta)
            with patch.object(driver,'activate',side_effect=ValueError('M2 injected activation failure')), \
                    patch.object(opening_storage,'load_image',side_effect=observe), \
                    patch.object(init,'verify_current_masters',wraps=init.verify_current_masters) as audit, \
                    patch.object(families,'_build_expected',wraps=families._build_expected) as expected_bags, \
                    self.assertRaisesRegex(ValueError,'injected activation'):
                call(True)
            self.assertEqual(audit.call_count,1)
            self.assertEqual(expected_bags.call_count,2)
            self.assertIsNot(expected_bags.call_args_list[0].kwargs['frame'],expected_bags.call_args_list[1].kwargs['frame'])
            self.assertEqual(len(images),len(set(images)))
            owner=ProductionInitialization.objects.select_related('source').get()
            cert=InitializationCertification.objects.get()
            self.assertEqual(owner.input_payload['schema'],V3)
            self.assertEqual(cert.families,list(range(1,14)))
            self.assertEqual(list(MdmFamilySource.objects.order_by('master_id').values_list('master_id',flat=True)),list(range(2,14)))
            self.assertFalse(any(path.endswith('/shape') for path in owner.input_payload['images']))
            self.assertIn('input/opening/state/controls/importer_settings',owner.input_payload['aliases'])
            self.assertFalse(any(path.startswith('input/opening/state/controls/importer_settings/') for path in owner.input_payload['images']))
            observed=init.read_initialized_input(owner)
            self.assertEqual(digest(observed),digest(expected))
            seals=(owner.pk,owner.source_id,owner.input_manifest_digest,owner.receipt_digest)
            # Simulate a kill after master/certification commit but before the
            # initialization receipt was written. Recover exactly those rows.
            checkpoint=json.loads(receipt.read_text());checkpoint.pop('initialization')
            checkpoint['phase']='INITIALIZATION';driver.write_receipt(receipt,checkpoint)
            with patch('mta.application.initialization_csv.read_prepared',side_effect=AssertionError('CSV reparse')), \
                    patch.object(register_mta,'register',side_effect=AssertionError('Registration replay')), \
                    patch.object(init,'initialize_complete',side_effect=AssertionError('Master reload')):
                result=call(True)
                self.assertEqual(result['families']['status'],'MDM_FAMILIES_READY')
                # Idempotent resume does not append another activation.
                self.assertEqual(call(True)['families']['certification_id'],str(cert.pk))
            owner.refresh_from_db()
            self.assertEqual(seals,(owner.pk,owner.source_id,owner.input_manifest_digest,owner.receipt_digest))
            self.assertEqual(CalculationRun.objects.count(),0)
            # Public complete re-entry is safe after activation, even while its
            # initializer owns the transaction; it must not call public readiness.
            with driver.installer_login():
                with patch.object(certification,'certify_locked',side_effect=AssertionError('Reseal')):
                    again,created=init.initialize_complete(csv_raw,manifest['native_input_sha256'],**args)
                    self.assertFalse(created);self.assertEqual(again.pk,owner.pk)
            from mta.runtime.ingestion_admission import readiness
            with patch.object(init,'read_initialized_input',side_effect=AssertionError('Readiness full scan')):
                self.assertEqual(readiness(owner.pk).source_digest,owner.source.digest)
            print('M2_POSTGRES_PASS parse-owned atomic-family/final-audit rollback activation-resume '
                f'all13 typed-opening uniform-shape/alias-no-duplicate unique-image-reads={len(images)} no-daily-run')
