"""Upgrade only the reviewed 687adcf opening without loading or resealing it.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import argparse
import json
import os
from pathlib import Path
import time
from mta.runtime.opening_scope import opening_operation


def retained(owner):
    from mta.runtime.mdm_models import MdmFamilySource
    from mta.runtime.mdm_integration_models import MdmSourceIntegration
    from mta.serialization import digest
    return dict(initialization=str(owner.pk),source=owner.source.digest,
        initialization_fields={f.attname:str(getattr(owner,f.attname)) for f in owner._meta.fields
            if f.name!='input_payload'},manifest=digest(owner.input_payload),
        source_fields={f.attname:str(getattr(owner.source,f.attname)) for f in owner.source._meta.fields},
        families=list(MdmFamilySource.objects.filter(source=owner.source).order_by('master_id').values(
            'master_id','digest','receipt')),
        integration=list(MdmSourceIntegration.objects.filter(source=owner.source).values('digest','receipt')))


@opening_operation
def transition(initialization_id,original_audit):
    """One atomic DDL/certification transition; failures leave the old DB intact."""
    from django.db import connection,transaction
    from django.db.migrations.executor import MigrationExecutor
    from psycopg import sql
    from release.native_identity import require_current
    from mta.serialization import digest
    from mta.runtime.models import ProductionInitialization,CalculationRun
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.ingestion_context import CONTRACT
    from mta.runtime import ingestion_upgrade as upgrade,ingestion_authority as authority
    from mta.runtime.ingestion_admission import registration,validate_activation,_admit
    from mta.runtime.opening_scope import opening_scope
    from mta.mdm import owned_namespace as owned
    release=require_current();start=time.monotonic()
    # Decode/hash immutable typed populations before holding a DDL/write
    # transaction. The operation cache is keyed by the complete original seal;
    # current masters and all live authority are rechecked under locks below.
    with connection.cursor() as cursor:
        cursor.execute('SELECT to_regclass(%s)',[authority.TABLE])
        installed=cursor.fetchone()[0] is not None
        if not installed:
            original,capability=upgrade.original_catalogue(cursor)
            prepared_owner=ProductionInitialization.objects.select_related('source').get(pk=initialization_id)
            prepared_seal=retained(prepared_owner)
            from mta.mdm import production_families as families
            with upgrade.auditing(prepared_owner,original,capability):
                families._verified_initialization(prepared_owner.source)
                families.require_binding(prepared_owner.source,read_only=True)
            print('UPGRADE_IMMUTABLE_OPENING_AUDIT_PASS',flush=True)
    with opening_scope(),transaction.atomic(),connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        cursor.execute('SELECT rolsuper FROM pg_roles WHERE rolname=current_user')
        if cursor.fetchone()!=(True,):
            raise ValueError('Explicit trusted maintenance provisioning session required')
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('fresh.production.initialization',0))")
        cursor.execute('LOCK TABLE mta.fresh_mta_productioninitialization, mta.fresh_mta_mdmsource, '
            'mta.fresh_mta_calculationrun IN ACCESS EXCLUSIVE MODE')
        owner=ProductionInitialization.objects.select_related('source').get(pk=initialization_id)
        before=retained(owner)
        if CalculationRun.objects.exists() or MdmDailyInputCapture.objects.exists():
            raise ValueError('This transition supports only the unused loaded opening')
        cursor.execute('SELECT to_regclass(%s)',[authority.TABLE])
        if cursor.fetchone()[0] is not None:
            # An already committed upgrade may be checked, never rebuilt.
            original,capability=registration(cursor);upgrade.baseline(capability)
            result=_admit(cursor,owner.pk,release)
            return dict(status='EXISTING_INGESTION_UPGRADE_VERIFIED',initialization_id=str(owner.pk),
                certification_digest=result.certification_digest)
        original,capability=upgrade.original_catalogue(cursor)
        if before!=prepared_seal:
            raise ValueError('Original opening changed after preparation')
        old_catalogue=owned._application_catalogue(cursor)
        if (original_audit.get('schema')!='vectorflow-original-upgrade-audit-v1'
                or original_audit.get('release')!=upgrade.BASELINE_IDENTITY
                or original_audit.get('receipt_digest')!=digest({k:v for k,v in original_audit.items() if k!='receipt_digest'})
                or original_audit.get('initialization_id')!=str(owner.pk)
                or original_audit.get('source_digest')!=owner.source.digest
                or original_audit.get('content_digest')!=owner.input_digest
                or original_audit.get('manifest_digest')!=owner.input_manifest_digest
                or original_audit.get('input_sha256')!=owner.input_sha256
                or original_audit.get('initialization_receipt_digest')!=owner.receipt_digest
                or original_audit.get('registration')!=owned._receipt_identity(original)):
            raise ValueError('Original independent full-audit receipt differs')
        executor=MigrationExecutor(connection)
        recorded=sorted([list(v) for v in executor.loader.applied_migrations])
        if recorded!=original_audit.get('migrations'):
            raise ValueError('Original migration prefix differs')
        plan=executor.migration_plan(executor.loader.graph.leaf_nodes())
        names=[migration.name for migration,backwards in plan]
        if (len(names)!=10 or any(backwards or migration.app_label!='fresh_mta' for migration,backwards in plan)
                or [name[:4] for name in names]!=[f'{i:04}' for i in range(144,154)]):
            raise ValueError('Only the exact ten ingestion migrations may be applied')
        cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(original['owner']['name'])))
        executor.migrate(executor.loader.graph.leaf_nodes())
        cursor.execute('RESET ROLE')
        authority.bootstrap(cursor,[original['owner']['name'],original['consumer']['name']])
        # Only newly introduced relations/functions receive their normal finite
        # production grants. Existing capability and every old ACL remain intact.
        catalogue=owned._application_catalogue(cursor)
        old_objects={obj['oid'] for obj in old_catalogue['objects']}
        old_functions={obj['oid'] for obj in old_catalogue['functions']}
        for obj in catalogue['objects']:
            if obj['kind']!='S' and obj['oid'] not in old_objects:
                schema,name=obj['name'].split('.',1)
                cursor.execute(sql.SQL('GRANT SELECT ON {}.{} TO {}').format(
                    sql.Identifier(schema),sql.Identifier(name),sql.Identifier(original['consumer']['name'])))
        for function in catalogue['functions']:
            if function['oid'] in old_functions:
                continue
            cursor.execute('SELECT %s::oid::regprocedure::text',[function['oid']])
            identity=cursor.fetchone()[0]
            cursor.execute('REVOKE EXECUTE ON FUNCTION '+identity+' FROM PUBLIC')
        current_catalogue=owned._application_catalogue(cursor)
        old_acl_names={(row['scope'],row['name']) for row in old_catalogue['grants']}
        if [row for row in current_catalogue['grants'] if (row['scope'],row['name']) in old_acl_names]!=old_catalogue['grants']:
            raise ValueError('Upgrade changed an original privilege')
        owned._check_application_grants(current_catalogue,original,logistics=True,production=True)
        owned._check_application_write_guards(cursor,original)
        from mta.runtime.ingestion_certification import certify_locked
        cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(original['owner']['name'])))
        with upgrade.auditing(owner,original,capability):
            cert=certify_locked(owner.pk,release,cursor)
        print('UPGRADE_FULL_CERTIFICATION_PASS',flush=True)
        from mta.runtime.ingestion_models import IngestionReleaseCompatibility
        body=dict(contract=CONTRACT,initialization_id=str(owner.pk),namespace=original['registration_id'],
            database_name=cert.database_name,database_oid=cert.database_oid,source_digest=owner.source.digest,
            original_registration_digest=digest(original),original_capability_digest=capability['receipt_digest'],
            original_commit=capability['release_identity']['source_commit'],
            original_release=capability['release_identity']['manifest_sha256'],
            target_commit=release['source_commit'],target_release=release['manifest_sha256'],
            certification_digest=cert.receipt_digest,schema_digest=cert.schema_digest,guard_digest=cert.guard_digest)
        audit={key:body[key] for key in ('original_release','target_release','original_commit','target_commit',
            'contract','original_registration_digest','schema_digest','certification_digest')}
        IngestionReleaseCompatibility.objects.create(initialization=owner,**audit,receipt_digest=digest(audit))
        cursor.execute('RESET ROLE')
        authority.append(cursor,body)
        validate_activation(cursor,body)
        owner.refresh_from_db();owner.source.refresh_from_db()
        if retained(owner)!=before or registration(cursor)!=(original,capability):
            raise ValueError('Upgrade changed original sealed opening or capability')
        result=_admit(cursor,owner.pk,release)
    return dict(status='INGESTION_UPGRADE_COMMITTED_ORIGINAL_OPENING_PRESERVED',
        initialization_id=str(owner.pk),source_digest=owner.source.digest,content_digest=owner.input_digest,
        certification_digest=result.certification_digest,target_release=release,seconds=time.monotonic()-start)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initialization-id',required=True)
    parser.add_argument('--original-audit',type=Path,required=True)
    args=parser.parse_args()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','release.mta_settings')
    import django
    django.setup()
    print(json.dumps(transition(args.initialization_id,json.loads(args.original_audit.read_text())),sort_keys=True))
