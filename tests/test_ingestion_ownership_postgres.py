"""Real migrated PostgreSQL guard/admission proof in one disposable empty DB.

Metadata fixtures exercise authority mechanics, not business-data certification,
calculation or a live opening upgrade. All fixture changes roll back per test.
"""
import os
import json
import time
from uuid import uuid4
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.db import connection, transaction, DatabaseError
from mta.serialization import digest
from mta.runtime import ingestion_authority as authority
from mta.runtime import ingestion_admission as admission
from mta.runtime.ingestion_context import CONTRACT, FAMILIES, RevisionCut
from mta.runtime.ingestion_models import (InitializationCertification, IngestionRevisionState,
    MasterInputRevision, IngestionReleaseCompatibility)
from mta.runtime.initialization_models import ProductionInitialization
from mta.runtime.mdm_models import MdmSource, MdmFamilySource
from mta.runtime.mdm_integration_models import MdmSourceIntegration

OWNER = 'vectorflow_mta_owner'
INSTALLER = 'vectorflow_mta_installer'
RUNTIME = 'vectorflow_mta_runtime'
ROLES = [OWNER, INSTALLER, RUNTIME]


@unittest.skipUnless(os.environ.get('VF_INGESTION_POSTGRES_PROOF') == '1', 'Explicit empty PostgreSQL proof required')
class IngestionPostgresTests(unittest.TestCase):
    proof_database = 'vf_ingestion_m1_20261020'

    def setUp(self):
        if connection.settings_dict['NAME'] != self.proof_database:
            raise RuntimeError('Proof must never target a working application database')
        self.atomic = transaction.atomic()
        self.atomic.__enter__()
        self.addCleanup(self.rollback)
        with connection.cursor() as c:
            c.execute('SELECT current_user')
            self.assertEqual(c.fetchone(), ('postgres',))
            # Test-only registrar fixture. No original capability is copied,
            # altered or accepted from another database.
            c.execute('CREATE SCHEMA fresh_control AUTHORIZATION fresh_namespace_registrar')
            c.execute('''CREATE TABLE fresh_control.owned_namespace (
              singleton boolean PRIMARY KEY DEFAULT TRUE, registration_id uuid, policy text,
              database_oid oid, database_name name, owner_oid oid, issuer_oid oid,
              consumer_oid oid, acceptor_oid oid, artifact_sha256 text, adapter_sha256 text)''')
            c.execute('ALTER TABLE fresh_control.owned_namespace OWNER TO fresh_namespace_registrar')
            c.execute('GRANT USAGE ON SCHEMA fresh_control TO '+OWNER+','+RUNTIME)
            c.execute('GRANT SELECT ON fresh_control.owned_namespace TO '+OWNER+','+RUNTIME)
            self.namespace = str(uuid4())
            c.execute('''INSERT INTO fresh_control.owned_namespace SELECT TRUE,%s,
              'fresh-owned-mdm-namespace-v1',d.oid,d.datname,o.oid,i.oid,r.oid,a.oid,%s,%s
              FROM pg_database d,pg_roles o,pg_roles i,pg_roles r,pg_roles a
              WHERE d.datname=current_database() AND o.rolname=%s AND i.rolname=%s
                AND r.rolname=%s AND a.rolname='fresh_operational_acceptor' ''',
                [self.namespace,'a'*64,'b'*64,*ROLES])
            c.execute('CREATE TABLE fresh_control.application_capability (singleton boolean PRIMARY KEY DEFAULT TRUE,binding jsonb)')
            c.execute('ALTER TABLE fresh_control.application_capability OWNER TO fresh_namespace_registrar')
            c.execute('GRANT SELECT ON fresh_control.application_capability TO '+OWNER+','+RUNTIME)
            from mta.mdm import owned_namespace as owned
            fixture_registration = owned._registered_identity(c)
            capability = dict(policy=owned.PRODUCTION_APPLICATION_POLICY,
                original_registration=owned._receipt_identity(fixture_registration),
                original_implementation_sha256='b'*64, implementation_sha256='b'*64,
                profile_digest='c'*64,objects_digest='d'*64,grants_digest='e'*64,schema_digest='f'*64,
                release_identity=dict(schema='vectorflow-native-release-source-v1',
                    source_commit=admission.BASELINE_RELEASE, manifest_sha256=admission.BASELINE_MANIFEST,
                    implementation_sha256='b'*64,source_files_digest='c'*64,migrations_digest='d'*64))
            capability['receipt_digest'] = digest(capability)
            c.execute('INSERT INTO fresh_control.application_capability VALUES(TRUE,%s::jsonb)', [json.dumps(capability)])
            authority.bootstrap(c, [OWNER,RUNTIME])
            for table, kind in (('fresh_mta_mdmskuloccurrent','mixed'), ('input_ingestion_proof','fact'),
                    ('proof_request','action'), ('proof_configuration','configuration'), ('proof_operating','operational')):
                c.execute('CREATE TABLE mta_state.'+table+'(id integer,"Norm" integer,"MinNorm" integer)')
                c.execute('ALTER TABLE mta_state.'+table+' OWNER TO '+OWNER)
                self.watch(c, 'mta_state', table, kind)
            c.execute('CREATE TABLE mta_opening.proof_population(id integer)')
            c.execute('ALTER TABLE mta_opening.proof_population OWNER TO '+OWNER)
            self.watch(c, 'mta_opening', 'proof_population', 'immutable')
            c.execute('INSERT INTO mta_state.fresh_mta_mdmskuloccurrent VALUES(1,10,2),(2,NULL,3)')
            c.execute('INSERT INTO mta_opening.proof_population VALUES(1)')
            c.execute('GRANT USAGE ON SCHEMA mta,mta_state,mta_opening TO '+RUNTIME)
            c.execute('GRANT SELECT ON ALL TABLES IN SCHEMA mta,mta_state,mta_opening TO '+RUNTIME)
            c.execute('GRANT UPDATE ON mta_state.fresh_mta_mdmskuloccurrent TO '+RUNTIME)
            # Fixture setup alone bypasses unrelated native business guards.
            # Normal replica mode is restored before all guards under test.
            c.execute('SET LOCAL session_replication_role=replica')
            source_receipt = dict(families={'1': {'fixture': 'master1'}}, schema='TEST_METADATA_ONLY')
            self.source = MdmSource.objects.create(digest=digest(source_receipt), database_name=connection.settings_dict['NAME'],
                dll_digest='', implementation_digest='a'*64, receipt=source_receipt)
            self.owner = ProductionInitialization.objects.create(source=self.source, opening_identity=str(uuid4()),
                opening_date='2026-04-07', input_sha256='a'*64, recipe_sha256='b'*64,
                configuration_digest='c'*64, implementation_digest='d'*64, input_digest='e'*64,
                input_manifest_digest='f'*64)
            families = {'1': digest(source_receipt['families']['1'])}
            for mid in FAMILIES[1:]:
                value = {'fixture': mid}
                families[str(mid)] = digest(value)
                MdmFamilySource.objects.create(source=self.source, master_id=mid,digest=digest(value),receipt=value)
            seal = dict(families=families)
            self.integration = MdmSourceIntegration.objects.create(source=self.source,digest=digest(seal),receipt=seal)
            c.execute('SET LOCAL session_replication_role=origin')
            from release.native_schema import schema_digest
            c.execute('SELECT current_database(),oid::bigint FROM pg_database WHERE datname=current_database()')
            database, oid = c.fetchone()
            body = dict(id=uuid4(),initialization_id=self.owner.pk,contract=CONTRACT,database_name=database,
                database_oid=oid,namespace=self.namespace,source_digest=self.source.digest,content_digest='e'*64,
                configuration_digest='c'*64,schema_digest=schema_digest(c),guard_digest=admission.security_digest(c,ROLES),
                release_digest='1'*64,populations=dict(opening_manifest='f'*64,integration=self.integration.digest),
                families=list(FAMILIES),authority_roles=ROLES)
            self.cert = InitializationCertification.objects.create(**body,receipt_digest=admission.receipt(body))
            IngestionRevisionState.objects.create(initialization=self.owner)
            revision = dict(id=uuid4(),initialization_id=self.owner.pk,parent_id=None,run_id=None,
                master_epoch=0,configuration_epoch=0,partitions={'opening_master_root': 'f'*64})
            self.revision = MasterInputRevision.objects.create(**revision,status='ACCEPTED',receipt_digest=admission.receipt(revision))
            original, capability = admission.registration(c)
            self.body = dict(contract=CONTRACT,initialization_id=str(self.owner.pk),namespace=self.namespace,
                database_name=database,database_oid=oid,source_digest=self.source.digest,
                original_registration_digest=digest(original),original_capability_digest=capability['receipt_digest'],
                original_commit=admission.BASELINE_RELEASE,original_release=admission.BASELINE_MANIFEST,
                target_commit='2'*40,target_release='1'*64,certification_digest=self.cert.receipt_digest,
                schema_digest=body['schema_digest'],guard_digest=body['guard_digest'])
            self.release = dict(source_commit=self.body['target_commit'],manifest_sha256=self.body['target_release'])
            self.compatibility(c)
            authority.append(c,self.body)

    def rollback(self):
        transaction.set_rollback(True)
        self.atomic.__exit__(None,None,None)

    def watch(self,c,schema,table,kind):
        for op, ref in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),
                        ('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
            c.execute('CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON '+schema+'.'+table+
                (' REFERENCING '+ref if ref else '')+' FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch(%s)',[kind])

    def compatibility(self,c):
        values = {k:self.body[k] for k in ('original_release','target_release','original_commit','target_commit',
            'contract','original_registration_digest','schema_digest','certification_digest')}
        IngestionReleaseCompatibility.objects.create(initialization=self.owner,**values,receipt_digest=digest(values))

    def admit(self):
        with connection.cursor() as c: return admission._admit(c,self.owner.pk,self.release)

    def epochs(self):
        return tuple(IngestionRevisionState.objects.filter(initialization=self.owner).values_list(*admission.EPOCHS).get())

    def rejected_sql(self,sql):
        with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as c: c.execute(sql)

    def test_complete_bounded_readiness_has_no_business_population_reads(self):
        from django.test.utils import CaptureQueriesContext
        start=time.monotonic()
        with CaptureQueriesContext(connection) as queries, \
                patch('mta.mdm.initialization.read_initialized_input',side_effect=AssertionError('Opening read')):
            state=self.admit()
        elapsed=time.monotonic()-start
        self.assertEqual(state.revisions,RevisionCut(0,0,0,0,0))
        self.assertLess(elapsed,5)
        # Inspect actual executed SQL, not just mocked call counts.
        text='\n'.join(q['sql'].lower() for q in queries)
        self.assertNotIn('"input_payload"',text)
        self.assertNotIn('from "mta_opening"',text)
        self.assertNotIn('from "mta_state"',text)
        print('CERTIFIED_READINESS_SECONDS',round(elapsed,4),'QUERIES',len(queries))

    def test_norm_only_changes_operational_generation_and_rollback_restores_cut(self):
        original=self.cert.receipt_digest
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute('SET LOCAL ROLE '+RUNTIME)
                c.execute('UPDATE mta_state.fresh_mta_mdmskuloccurrent SET "Norm"=11 WHERE id=1')
                c.execute('RESET ROLE')
            self.assertEqual(self.epochs(),(0,0,0,1,0))
            self.assertEqual(self.admit().revisions.operational,1)
            transaction.set_rollback(True)
        self.assertEqual(self.epochs(),(0,0,0,0,0))
        self.cert.refresh_from_db()
        self.assertEqual(self.cert.receipt_digest,original)

    def test_static_master_change_invalidates_accepted_revision(self):
        with connection.cursor() as c:
            c.execute('UPDATE mta_state.fresh_mta_mdmskuloccurrent SET "MinNorm"=9 WHERE id=1')
        self.assertEqual(self.epochs(),(1,1,0,1,0))
        with self.assertRaises(MasterInputRevision.DoesNotExist): self.admit()

    def test_actual_supplier_raw_change_invalidates_configuration_revision(self):
        from mta.runtime.mdm_supplier_models import MdmMoqRaw2
        with connection.cursor() as c:
            # Existing supplier writer guard requires its owned bootstrap token
            # for this otherwise-empty metadata fixture. No calculation is run.
            c.execute("SELECT set_config('fresh.mdm_supplier_bootstrap',%s,true)",[str(self.source.pk)])
        MdmMoqRaw2.objects.create(source=self.source,ordinal=1,SKUCode='PROOF',WHCode='PROOF',
            SupplierCode='PROOF',SupplierDescription=None,MOQ=2)
        self.assertEqual(self.epochs(),(0,1,0,0,0))
        with self.assertRaises(MasterInputRevision.DoesNotExist): self.admit()

    def test_fact_configuration_action_operational_and_noop_coverage(self):
        with connection.cursor() as c:
            c.execute('UPDATE mta_state.fresh_mta_mdmskuloccurrent SET "Norm"="Norm"')
            c.execute('UPDATE mta_state.fresh_mta_mdmskuloccurrent SET "Norm"=7 WHERE id=999')
            self.assertEqual(self.epochs(),(0,0,0,0,0))
            for table in ('input_ingestion_proof','proof_configuration','proof_request','proof_operating'):
                c.execute('INSERT INTO mta_state.'+table+' VALUES(1,NULL,NULL)')
        self.assertEqual(self.epochs(),(0,1,1,1,1))

    def test_immutable_rows_certification_and_authority_cannot_be_rewritten(self):
        self.rejected_sql('UPDATE mta_opening.proof_population SET id=2')
        self.rejected_sql('TRUNCATE mta_opening.proof_population')
        self.rejected_sql("UPDATE mta.fresh_mta_initializationcertification SET content_digest='bad'")
        self.rejected_sql('UPDATE fresh_control.ingestion_release_authority SET receipt_digest=receipt_digest')
        self.rejected_sql('TRUNCATE fresh_control.ingestion_release_authority')
        self.cert.status='INVALIDATED'
        self.cert.save(update_fields=['status'])
        self.rejected_sql("UPDATE mta.fresh_mta_initializationcertification SET status='CERTIFIED'")
        with self.assertRaises(InitializationCertification.DoesNotExist): self.admit()

    def test_runtime_and_application_owner_cannot_forge_transition(self):
        for role in (OWNER,RUNTIME):
            with self.subTest(role=role), self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as c:
                c.execute('SET LOCAL ROLE '+role)
                c.execute('INSERT INTO fresh_control.ingestion_release_authority SELECT * FROM fresh_control.ingestion_release_authority')
        for role in (OWNER,RUNTIME):
            with self.subTest(role=role), transaction.atomic(), connection.cursor() as c:
                c.execute('SET LOCAL ROLE '+role)
                with self.assertRaises(ValueError): authority.append(c,self.body)
        self.rejected_sql('SET LOCAL ROLE '+RUNTIME+'; UPDATE mta.fresh_mta_ingestionrevisionstate SET master_epoch=99')

    def test_missing_foreign_corrupt_and_partial_transition_fail_closed(self):
        with connection.cursor() as c:
            with self.assertRaises(ValueError): authority.read(c,uuid4(),self.body['target_release'])
        for key,value in (('database_oid',1),('namespace',str(uuid4())),('original_commit','0'*40),
                          ('target_release','0'*64),('certification_digest','0'*64)):
            with self.subTest(key=key),connection.cursor() as c,self.assertRaises(ValueError):
                admission.validate_activation(c,{**self.body,key:value})
        with self.assertRaises(ValueError),connection.cursor() as c:
            admission._admit(c,self.owner.pk,{**self.release,'source_commit':'0'*40})
        # A different target has no activated row, even if metadata exists.
        with self.assertRaises(ValueError),connection.cursor() as c:
            admission._admit(c,self.owner.pk,{**self.release,'manifest_sha256':'3'*64})
        with patch.object(admission,'_certificate',return_value={**admission._certificate(self.owner.pk),'receipt_digest':'0'*64}):
            with self.assertRaises(ValueError): self.admit()

    def test_missing_writer_or_privilege_drift_invalidates_admission(self):
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute('ALTER TABLE mta_state.input_ingestion_proof DISABLE TRIGGER ingestion_watch_insert')
            with self.assertRaises(ValueError): self.admit()
            transaction.set_rollback(True)
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute('GRANT INSERT ON mta.fresh_mta_initializationcertification TO '+RUNTIME)
            with self.assertRaises(ValueError): self.admit()
            transaction.set_rollback(True)
        with transaction.atomic():
            with connection.cursor() as c: c.execute('CREATE TABLE mta_state.unclassified_writer(id integer)')
            with self.assertRaises(ValueError): self.admit()
            transaction.set_rollback(True)
        self.admit()


@unittest.skipUnless(os.environ.get('VF_INGESTION_POSTGRES_PROOF') == '1', 'Explicit empty PostgreSQL proof required')
class ZFreshCertificationFlow(unittest.TestCase):
    """Real registration→typed initialization→full audit→activation→readiness.

    Runs last in the disposable DB. Native source authentication is tested by
    test_native_release_identity; only its already-admitted identity is mocked
    here because no uncommitted source image is built for milestone1.
    """
    def test_current_release_registration_and_complete_certification(self):
        from pathlib import Path
        from django.conf import settings
        from release.register_mta import render_sql
        from mta.mdm import owned_namespace as owned
        from mta.mdm.application_registration import register_application
        from mta.mdm.initialization import current_implementation_digest, initialize
        from mta.mdm.production_families import bootstrap_native_families
        from tests.initialization_input_fixture import supplied_input, encoded
        from mta.runtime.ingestion_certification import certify_current
        if connection.settings_dict['NAME'] != 'vf_ingestion_m1_20261020':
            raise RuntimeError('Disposable empty proof database required')
        original_options=dict(connection.settings_dict['OPTIONS'])
        original_user=connection.settings_dict['USER']
        original_password=connection.settings_dict['PASSWORD']
        def login(user,password,role=None):
            connection.close()
            connection.settings_dict.update(USER=user,PASSWORD=password,OPTIONS=dict(original_options))
            if role: connection.settings_dict['OPTIONS']['options'] += ' -c role='+role
        def restore(): login(original_user,original_password)
        self.addCleanup(restore)
        value=supplied_input()
        value['opening']['state']['importer_settings'] += [
            dict(Parameter='NMSMOQInputDataFormat',Value='WithDestLoc'),
            dict(Parameter='ActivateNMSUIUploadLogs',Value='0')]
        raw,input_sha,args=encoded(value)
        implementation=current_implementation_digest()
        release=dict(schema='vectorflow-native-release-source-v1',source_commit='4'*40,
            manifest_sha256='5'*64,implementation_sha256=implementation,
            source_files_digest='6'*64,migrations_digest='7'*64)
        with patch('release.native_identity.require_current',return_value=release):
            with transaction.atomic(),connection.cursor() as c:
                c.execute('SELECT current_database(),oid::bigint FROM pg_database WHERE datname=current_database()')
                database,oid=c.fetchone()
                template=Path('release/owned-namespace.sql').read_text()
                # Global role membership is pre-existing and protected. Only
                # database-local namespace/grants are installed in this test.
                template=template.replace('GRANT :"owner_role", fresh_operational_acceptor TO :"issuer_role";', '')
                values=dict(database_name=database,owner_role=OWNER,issuer_role=INSTALLER,consumer_role=RUNTIME,
                    registration_id=str(uuid4()),artifact_sha256=input_sha,adapter_sha256=implementation)
                c.execute(render_sql(template,values))
                for schema in ('mta_state','mta_opening'):
                    c.execute('GRANT USAGE ON SCHEMA '+schema+' TO '+RUNTIME+',fresh_operational_acceptor')
                authority.bootstrap(c,[OWNER,RUNTIME])
                registration=owned._registered_identity(c)
                original=owned._receipt_identity(registration)
                binding=register_application(c,expected_database=database,expected_database_oid=oid,
                    expected_registration_digest=original['registration_digest'],
                    expected_original_implementation=implementation,implementation_sha256=implementation,production=True)
                self.assertEqual(owned._registered_identity(c),registration)
            login(INSTALLER,Path('/run/secrets/mta_installer_password').read_text().strip(),OWNER)
            owner,created=initialize(raw,input_sha,**args)
            self.assertTrue(created)
            bootstrap_native_families(owner)
            original_seals=(owner.input_sha256,owner.input_digest,owner.receipt_digest,owner.source.digest)
            cert=certify_current(owner.pk)
            owner.refresh_from_db()
            self.assertEqual(original_seals,(owner.input_sha256,owner.input_digest,owner.receipt_digest,owner.source.digest))
            self.assertEqual(cert.families,list(FAMILIES))
            self.assertEqual(cert.populations['opening_manifest'],owner.input_manifest_digest)
            self.assertEqual(IngestionRevisionState.objects.get(initialization=owner).master_epoch,0)
            # Certification alone is intentionally not READY.
            with self.assertRaises(ValueError),connection.cursor() as c:
                admission._admit(c,owner.pk,release)
            login(original_user,original_password)
            with transaction.atomic(),connection.cursor() as c:
                reg,cap=admission.registration(c)
                body=dict(contract=CONTRACT,initialization_id=str(owner.pk),namespace=reg['registration_id'],
                    database_name=database,database_oid=oid,source_digest=owner.source.digest,
                    original_registration_digest=digest(reg),original_capability_digest=cap['receipt_digest'],
                    original_commit=release['source_commit'],original_release=release['manifest_sha256'],
                    target_commit=release['source_commit'],target_release=release['manifest_sha256'],
                    certification_digest=cert.receipt_digest,schema_digest=cert.schema_digest,guard_digest=cert.guard_digest)
                audit={k:body[k] for k in ('original_release','target_release','original_commit','target_commit','contract',
                    'original_registration_digest','schema_digest','certification_digest')}
                IngestionReleaseCompatibility.objects.create(initialization=owner,**audit,receipt_digest=digest(audit))
                authority.append(c,body)
            runtime_password=Path('/proof-secrets/mta_runtime_password').read_text().strip()
            login(RUNTIME,runtime_password)
            admission._process_release.cache_clear()
            self.addCleanup(admission._process_release.cache_clear)
            with patch.dict(os.environ,VF_NATIVE_RELEASE_COMMIT=release['source_commit'],VF_NATIVE_RELEASE_SHA256=release['manifest_sha256']):
                with patch('mta.mdm.initialization.read_initialized_input',side_effect=AssertionError('Opening scan')), \
                        patch('mta.mdm.production_families._verified_initialization',side_effect=AssertionError('Full audit')):
                    self.assertEqual(admission.readiness(owner.pk).source_digest,owner.source.digest)
                    self.assertEqual(admission.certified_source(owner.source.digest).pk,owner.source_id)
                    with self.assertRaises(ValueError): certify_current(owner.pk)
            print('FRESH_CERTIFICATION_FLOW_PASS original_seals_preserved all13_families runtime_readiness')
