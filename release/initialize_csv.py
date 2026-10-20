"""One process owns CSV preparation, installation and certification activation.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile


def write_receipt(path, body):
    """Replace only the caller's locked onboarding receipt after each commit."""
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
            prefix='.'+path.name+'.', delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(body, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def installer_login():
    """Use the existing scoped credential; never grant or change any role."""
    from django.db import connection
    from release.provision import plan
    from release.configuration import secret
    roles = plan()['roles']['MTA']
    previous = {key: connection.settings_dict[key] for key in ('USER','PASSWORD','OPTIONS')}
    options = dict(previous['OPTIONS'])
    options['options'] = options.get('options','')+' -c role='+roles['OWNER']
    connection.close()
    connection.settings_dict.update(USER=roles['INSTALLER'], PASSWORD=secret('MTA_INSTALLER_PASSWORD'), OPTIONS=options)
    try:
        yield
    finally:
        connection.close()
        connection.settings_dict.update(previous)


def activate(owner):
    """Activate only this freshly certified current release; never upgrade."""
    from django.db import connection, transaction
    from release.native_identity import require_current
    from mta.serialization import digest
    from mta.runtime.ingestion_context import CONTRACT
    from mta.runtime.ingestion_models import InitializationCertification, IngestionReleaseCompatibility
    from mta.runtime import ingestion_admission as admission, ingestion_authority as authority
    release = require_current()
    with transaction.atomic(), connection.cursor() as cursor:
        original, capability = admission.registration(cursor)
        if capability['release_identity'] != release:
            raise ValueError('CSV completion cannot upgrade an older release')
        cert = InitializationCertification.objects.get(initialization=owner, status='CERTIFIED')
        body = dict(contract=CONTRACT, initialization_id=str(owner.pk), namespace=original['registration_id'],
            database_name=cert.database_name, database_oid=cert.database_oid, source_digest=owner.source.digest,
            original_registration_digest=digest(original), original_capability_digest=capability['receipt_digest'],
            original_commit=release['source_commit'], original_release=release['manifest_sha256'],
            target_commit=release['source_commit'], target_release=release['manifest_sha256'],
            certification_digest=cert.receipt_digest, schema_digest=cert.schema_digest, guard_digest=cert.guard_digest)
        cursor.execute('SELECT count(*) FROM fresh_control.ingestion_release_authority '
            'WHERE initialization_id=%s AND target_release=%s', [owner.pk,release['manifest_sha256']])
        if cursor.fetchone()[0]:
            if authority.read(cursor,owner.pk,release['manifest_sha256']) != body:
                raise ValueError('Existing CSV activation differs')
            admission.validate_activation(cursor,body)
        else:
            audit = {key: body[key] for key in ('original_release','target_release','original_commit',
                'target_commit','contract','original_registration_digest','schema_digest','certification_digest')}
            IngestionReleaseCompatibility.objects.create(initialization=owner,**audit,receipt_digest=digest(audit))
            authority.append(cursor,body)
    return str(cert.pk)


def registered_checkpoint(input_sha256):
    """Recover a committed registration, never create/adopt a different one."""
    from django.db import connection, transaction
    from mta.mdm.initialization import implementation_digest
    from mta.mdm.owned_namespace import authorize_install
    from mta.runtime.ingestion_admission import registration
    from release.native_identity import require_current
    from release.provision import plan
    release=require_current()
    with installer_login(), transaction.atomic():
        # The unchanged native installer guard verifies full schema/grants,
        # restricted roles, exact artifact, actual DB identity and producer.
        authorize_install(input_sha256,implementation_digest())
    with connection.cursor() as cursor:
        original,capability=registration(cursor)
    if original['database_name'] != plan()['databases']['MTA'] or capability['release_identity'] != release:
        raise ValueError('Recorded namespace belongs to another target/release')
    return dict(status='FRESH_CURRENT_SOURCE_CAPABILITY_REGISTERED_NO_INPUT_OR_CALCULATION',
        database=original['database_name'],database_oid=original['database_oid'],namespace=original['registration_id'],
        policy=capability['policy'],receipt_digest=capability['receipt_digest'],
        implementation_sha256=release['implementation_sha256'],release_identity=release,schema_digest=capability['schema_digest'])


def initial_result(owner):
    return dict(status='INITIALIZED',opening_id=str(owner.pk),source_id=owner.source_id,
        source_digest=owner.source.digest,input_sha256=owner.input_sha256,
        opening_date=owner.opening_date.isoformat(),content_digest=owner.input_digest,
        configuration_digest=owner.configuration_digest,recipe_digest=owner.recipe_sha256,accepted_day=False)


def finish_existing(owner):
    """Complete an exact current-release opening; never initialize it again."""
    from django.db import connection, transaction
    from mta.runtime.opening_scope import opening_scope
    from mta.mdm.initialization import _complete, read_initialized_input
    from mta.mdm.supplier_revisions import source_lock
    from mta.runtime.models import ProductionInitialization
    with installer_login(), opening_scope(), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('fresh.production.initialization',0))")
        with source_lock(owner.source_id):
            owner=ProductionInitialization.objects.select_for_update().select_related('source').get(pk=owner.pk)
            _complete(owner,read_initialized_input(owner))


def run(directory, manifest_sha256, configuration, recipe, receipt_path, *, resume=False):
    """Normal path parses once; resume admits only the exact recorded checkpoint."""
    from release.native_identity import require_current
    require_current()
    from mta.presentation.native_mode import require_configuration
    require_configuration()
    from mta.application.initialization_csv import read_prepared
    from mta.mdm.initialization import initialize_complete
    from mta.runtime.models import ProductionInitialization
    from release.csv_onboarding import reconcile
    from release.register_mta import register
    from django.db import connection, transaction
    receipt = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
    if receipt.get('manifest_sha256') != manifest_sha256:
        raise ValueError('Onboarding manifest checkpoint differs')
    # Bind the access/template bytes before registering or writing any master.
    import hashlib
    pins = {name:hashlib.sha256((Path(directory)/name).read_bytes()).hexdigest()
            for name in ('binding-template.json','permissions.json')}
    if receipt.get('pack_pins') != pins:
        raise ValueError('Onboarding access/template checkpoint differs')
    try:
        if not resume and receipt.get('registration'):
            raise ValueError('Recorded namespace requires explicit resume')
        if resume:
            manifest=(Path(directory)/'opening'/'opening-manifest.json').read_bytes()
            if hashlib.sha256(manifest).hexdigest()!=manifest_sha256:
                raise ValueError('Resume manifest bytes differ')
            manifest=json.loads(manifest)
            if (manifest['configuration_digest'],manifest['recipe_digest'])!=(configuration,recipe):
                raise ValueError('Resume manifest configuration differs')
            observed=registered_checkpoint(manifest['native_input_sha256'])
            if receipt.get('registration') and receipt['registration']!=observed:
                raise ValueError('Recorded namespace checkpoint differs')
            if not receipt.get('registration') and receipt['phase']!='REGISTRATION':
                raise ValueError('Unrecorded registration outside its commit checkpoint')
            receipt['registration']=observed
            # Recover the database commit before the host receipt write. This
            # admits only a current, same-input, no-day sealed opening; a full
            # audit below proves a lost initialization checkpoint independently.
            if not receipt.get('initialization') and ProductionInitialization.objects.exists():
                owner=ProductionInitialization.objects.select_related('source').get()
                if (owner.input_sha256,owner.configuration_digest,owner.recipe_sha256,owner.implementation_digest)!= (
                        manifest['native_input_sha256'],configuration,recipe,observed['implementation_sha256']):
                    raise ValueError('Unrecorded opening belongs to different input/release')
                recovered={**receipt,'initialization':initial_result(owner)}
                reconcile(recovered,directory)
                from mta.runtime.ingestion_models import InitializationCertification
                if InitializationCertification.objects.filter(initialization=owner).exists():
                    from mta.runtime.opening_scope import opening_scope
                    from mta.mdm.initialization import verify_current_masters
                    from mta.mdm.master_owners import owner_batches
                    from mta.mdm.production_families import _verified_initialization, require_binding
                    from mta.mdm.daily_input import _capture_pair_exclusions
                    with installer_login(), opening_scope(), transaction.atomic(), connection.cursor() as cursor:
                        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                        checked,frame=_verified_initialization(owner.source)
                        if checked.pk!=owner.pk:
                            raise ValueError('Recovered initialization owner differs')
                        verify_current_masters(owner.source,owner_batches(frame['opening']['state'],strict=True))
                        if _capture_pair_exclusions(owner.source)['rows']!=frame['pair_exclusions']:
                            raise ValueError('Recovered pair-exclusion readback differs')
                        require_binding(owner.source)
                else:
                    finish_existing(owner)
                receipt=recovered
            write_receipt(receipt_path,receipt)
        prepared = None
        if not receipt.get('initialization'):
            prepared = read_prepared(Path(directory)/'opening', manifest_sha256,
                expected_configuration=configuration,expected_recipe=recipe)
            if not resume:
                receipt['phase']='REGISTRATION'
                write_receipt(receipt_path,receipt)
                receipt['registration']=register(prepared.sha256)
                receipt['phase']='INITIALIZATION'
                write_receipt(receipt_path,receipt)
            with installer_login():
                owner,created=initialize_complete(prepared,prepared.sha256,
                    expected_configuration=configuration,expected_recipe=recipe)
                if not created:
                    raise ValueError('New onboarding unexpectedly found an opening')
                initial = initial_result(owner)
            receipt['initialization']=initial
            receipt['phase']='CERTIFICATION_ACTIVATION'
            write_receipt(receipt_path,receipt)
        else:
            # Already committed openings are never parsed/reloaded/resealed.
            owner = reconcile(receipt,directory)
            if (owner.configuration_digest,owner.recipe_sha256) != (configuration,recipe):
                raise ValueError('Existing opening configuration differs')
            from mta.runtime.ingestion_models import InitializationCertification
            if not InitializationCertification.objects.filter(initialization=owner).exists():
                finish_existing(owner)
        cert_id=activate(owner)
        receipt['families']=dict(status='MDM_FAMILIES_READY',opening_id=str(owner.pk),
            source_digest=owner.source.digest,input_sha256=owner.input_sha256,certification_id=cert_id,accepted_day=False)
        receipt['phase']='CONFIGURATION'
        receipt.pop('error',None)
        write_receipt(receipt_path,receipt)
        return receipt
    except Exception as error:
        receipt.update(status='STOPPED',error=str(error))
        write_receipt(receipt_path,receipt)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-directory',required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--configuration-digest',required=True)
    parser.add_argument('--recipe-digest',required=True)
    parser.add_argument('--receipt',required=True)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','release.mta_settings')
    import django
    django.setup()
    print(json.dumps(run(args.input_directory,args.manifest_sha256,args.configuration_digest,
        args.recipe_digest,args.receipt,resume=args.resume),sort_keys=True))


if __name__ == '__main__':
    main()
