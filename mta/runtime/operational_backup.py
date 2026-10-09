"""Owned PostgreSQL backup/restore effect; complete evidence stays on disk."""
import gzip
import io
import json
import os
import re
from django.db import connection,transaction
import psycopg

from mta.application.operational_io import owned_path, verify_file
from mta.application.operational_pg_backup import dump_database, restore_database, image_digest
from mta.application.operational_restore_qualification import compare_restore_images
from mta.runtime.operational_models import OperationalAttempt, OperationalBackup,OperationalOperation
from mta.runtime.operational_lease import require_attempt_lease,OperationalLeaseError
from mta.runtime.operational_attempts import configuration_value, _identity
from mta.runtime.operational_effects import operation, record_file

BACKUP_OPERATION=dict(name='PostgreSQLBackup',stage='post-backup',
    source_digest='4fa3ed4aaf5085db4e6c60897fb1c43cad601285bd355634a1dce23d2fa27150')
SOURCE_IMAGE='backup/logical-source.json.gz'
RESTORED_IMAGE='backup/logical-restored.json.gz'
OWNERSHIP_FILE='backup/ownership.json'


def _write_ownership(effect,value):
    path=owned_path(effect.attempt.root,OWNERSHIP_FILE)
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,sort_keys=True,separators=(',',':'))
    record_file(effect,relative_path=OWNERSHIP_FILE,role='backup-ownership-proof')


def _verify_ownership(backup,options):
    binding=options.get('owned_restore')
    if binding is None:return
    effect=backup.operation
    file=effect.files.get(relative_path=OWNERSHIP_FILE,role='backup-ownership-proof')
    verify_file(effect.attempt.root,dict(relative_path=file.relative_path,sha256=file.sha256,size_bytes=file.size_bytes))
    value=json.loads(owned_path(effect.attempt.root,OWNERSHIP_FILE).read_bytes())
    namespace=effect.attempt.run.mdm_input_capture.source.receipt['owned_namespace']
    expected=dict(policy='fresh-owned-restore-v1',registration_digest=binding['registration_digest'],
        source_database=options['source_database'],source_oid=binding['database_oid'],
        source_owner_oid=binding['owner_oid'],source_issuer_oid=namespace['issuer_oid'],
        provisioner_oid=binding['provisioner_oid'],provisioner_role=binding['provisioner_role'],
        target_database=backup.restore_target,target_oid=value.get('target_oid'),
        target_owner_oid=binding['provisioner_oid'],public_connect=False)
    if (value!=expected or type(value.get('target_oid')) is not int
            or value['target_oid']==value['source_oid']
            or any(binding[k]!=namespace[k] for k in ('registration_digest','database_oid','owner_oid'))):
        raise ValueError('Observed backup ownership receipt differs')


@transaction.atomic
def _save_backup(effect,backup=None,**values):
    owner=OperationalAttempt.objects.select_for_update().get(pk=effect.attempt_id)
    require_attempt_lease(owner)
    current=OperationalOperation.objects.select_for_update().get(pk=effect.pk)
    if owner.status!='RUNNING' or current.status!='RUNNING' or current.group!='O8':
        raise ValueError('Backup receipt requires a running operational owner')
    if backup is None:
        result=OperationalBackup.objects.create(operation=current,**values)
    else:
        result=OperationalBackup.objects.select_for_update().get(pk=backup.pk,operation=current)
        for name,value in values.items():setattr(result,name,value)
        result.save(update_fields=list(values))
    require_attempt_lease(owner)
    return result


def _write_image(effect,path,value):
    target=owned_path(effect.attempt.root,path)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as zipped:
            with io.TextIOWrapper(zipped,encoding='utf-8',newline='') as text:
                json.dump(value,text,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    return record_file(effect,relative_path=path,role='backup-logical-proof')


def _read_image(effect,path):
    receipt=effect.files.get(relative_path=path)
    verify_file(effect.attempt.root,dict(relative_path=path,sha256=receipt.sha256,size_bytes=receipt.size_bytes))
    with gzip.open(owned_path(effect.attempt.root,path),'rt',encoding='utf-8') as stream:
        return json.load(stream)


def verify_backup(backup):
    effect=backup.operation
    configuration=configuration_value(effect.attempt.configuration)
    options=configuration['bindings'].get('postgres_backup',{})
    if (backup.file.operation_id!=effect.pk or backup.database_system!='PostgreSQL'
            or backup.method!='pg_dump-custom-snapshot' or not backup.snapshot_identity
            or backup.restore_target!='fresh_cohort2_restore_'+effect.attempt_id.hex
            or backup.restore_status not in ('VERIFIED','QUALIFIED')
            or effect.group!='O8'
            or any(getattr(effect,key)!=value for key,value in BACKUP_OPERATION.items())
            or backup.database_name!=options.get('source_database')
            or backup.tool_sha256!=options.get('pg_dump_sha256')
            or (backup.qualification and backup.qualification!=options.get('qualification'))
            or backup.file.role!='postgres-backup'
            or backup.file.relative_path!='backup/post.dump'):
        raise ValueError('Operational backup ownership/method/restoration is unproved')
    verify_file(effect.attempt.root,dict(relative_path=backup.file.relative_path,
        sha256=backup.file.sha256,size_bytes=backup.file.size_bytes))
    _verify_ownership(backup,options)
    source=_read_image(effect,SOURCE_IMAGE);restored=_read_image(effect,RESTORED_IMAGE)
    result=compare_restore_images(source,restored,qualification=backup.qualification or None)
    if (result['status']!=backup.restore_status or result['logical_digest']!=backup.logical_digest
            or result['restored_digest']!=backup.restored_digest
            or result.get('qualification','')!=backup.qualification
            or result.get('qualification_sha256','')!=backup.qualification_sha256):
        raise ValueError('Operational backup complete logical proof differs')
    return result


def materialize_backup(attempt_id):
    owner=OperationalAttempt.objects.select_related('run','configuration').get(pk=attempt_id)
    config=configuration_value(owner.configuration)
    current=_identity(owner.run)
    if (owner.status!='RUNNING' or owner.run_output_digest!=current['output_digest']
            or any(getattr(owner,name)!=current[name] for name in ('action_digest','source_digest'))):
        raise ValueError('Exact running operational backup owner required')
    matches=[row for row in config['bindings'].get('operation_roster',[]) if row.get('group')=='O8']
    if len(matches)!=1 or {key:matches[0].get(key) for key in BACKUP_OPERATION}!=BACKUP_OPERATION:
        raise ValueError('Canonical post-backup operation roster required')
    for name in ('DoPostBkpImporter','DoPostBkpDBM','DoPostBkpBPR','DoPostBkpBTR','DBBkpCompress'):
        if [row['value'] for row in config['settings'] if row['name']==name]!=['1']:
            raise ValueError('Explicit generic post-backup configuration required: '+name)
    options=config['bindings'].get('postgres_backup')
    expected={'source_database','pg_dump_path','pg_dump_sha256','pg_restore_path','pg_restore_sha256','qualification'}
    if not isinstance(options,dict) or set(options) not in (expected,expected|{'owned_restore'}):
        raise ValueError('Explicit bounded PostgreSQL tool/database binding required')
    db=connection.settings_dict
    source=options['source_database']
    ownership=None
    if 'owned_restore' in options:
        from mta.runtime.owned_restore import bind_restore
        ownership=bind_restore(options['owned_restore'],source,
                              owner.run.mdm_input_capture.source.receipt,db)
    elif source!=db['NAME'] or not (source=='fresh_complete' or re.fullmatch(r'fresh_cohort2_[a-z0-9_]+',source)):
        raise ValueError('Backup must use the same owned application database')
    params=dict(host=db['HOST'],port=db['PORT'] or '5432',user=db['USER'],password=db['PASSWORD'])
    def connect(name):return psycopg.connect(dbname=name,**params)
    def admin():return psycopg.connect(dbname='postgres',autocommit=True,**params)
    environment={**os.environ,'PGHOST':str(params['host']),'PGPORT':str(params['port']),
                 'PGUSER':params['user'],'PGPASSWORD':params['password']}
    restore_connect=connect;restore_environment=environment
    if ownership is not None:
        source_options='-c role='+ownership.namespace['owner_role']
        def connect(name):return psycopg.connect(dbname=name,options=source_options,**params)
        environment={**environment,'PGOPTIONS':source_options}
        admin=ownership.admin;restore_connect=ownership.connect
        restore_environment=ownership.environment()
    target='fresh_cohort2_restore_'+owner.pk.hex
    with operation(owner,**matches[0]) as effect:
        captured=dump_database(connection_factory=connect,database_name=source,root=owner.root,
            relative_path='backup/post.dump',executable=options['pg_dump_path'],
            executable_sha256=options['pg_dump_sha256'],client_environment=environment,
            **({'ownership':ownership} if ownership is not None else {}))
        file=record_file(effect,relative_path=captured['file']['relative_path'],role='postgres-backup')
        _write_image(effect,SOURCE_IMAGE,captured['logical_image'])
        backup=_save_backup(effect,database_name=source,database_system='PostgreSQL',
            method='pg_dump-custom-snapshot',snapshot_identity=captured['snapshot'],tool_sha256=options['pg_dump_sha256'],
            file=file,logical_digest=captured['logical_digest'],restore_target=target,restore_status='RUNNING')
        try:
            def observed(image):
                nonlocal backup
                _write_image(effect,RESTORED_IMAGE,image)
                backup=_save_backup(effect,backup,restored_digest=image_digest(image))
            restored=restore_database(admin_connection_factory=admin,connection_factory=restore_connect,
                target_database=target,source_database=source,root=owner.root,backup=captured,
                executable=options['pg_restore_path'],executable_sha256=options['pg_restore_sha256'],
                client_environment=restore_environment,qualification=options['qualification'],observe_restore=observed,
                **({'ownership':ownership} if ownership is not None else {}))
            if ownership is not None:_write_ownership(effect,ownership.receipt(target))
            backup=_save_backup(effect,backup,restore_status=restored['status'],
                qualification=restored.get('qualification',''),
                qualification_sha256=restored.get('qualification_sha256',''))
            verify_backup(backup)
        except Exception:
            try:
                _save_backup(effect,backup,restore_status='FAILED')
            except OperationalLeaseError:
                pass
            raise
    return effect
