"""One explicit compatibility bridge for an already sealed native source.

Fresh sources bind v2 directly in their original integration seal. Historical
compatibility is a registrar-owned assertion, never an application-owned list
of acceptable code digests. No archived Python is imported or executed.
"""
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import uuid
from zipfile import ZipFile

from django.db import connection

from mta.mdm.location_projection import VERSION
from mta.serialization import digest

REGISTRY = 'mta.native_location_transition'
V1 = 'native-closing-locations-v1'
ROOT = Path(__file__).resolve().parents[2]


def source_files(root=ROOT):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for area in ('mta', 'vectorflow') for p in sorted((root/area).rglob('*'))
        if p.is_file() and p.suffix in ('.py', '.json') and '__pycache__' not in p.parts}


def source_manifest_digest():
    return digest(source_files())


def registration():
    """Return only a row under the original namespace's registrar ownership."""
    from mta.mdm.owned_namespace import REGISTRAR_ROLE
    with connection.cursor() as c:
        c.execute('SELECT to_regclass(%s)', [REGISTRY])
        if c.fetchone()[0] is None:
            return None
        c.execute("""SELECT r.rolname, r.rolcanlogin, r.rolsuper,
            r.rolcreatedb, r.rolcreaterole, r.rolreplication, r.rolbypassrls,
            pg_has_role(current_user,r.oid,'MEMBER')
            FROM pg_class t JOIN pg_roles r ON r.oid=t.relowner
            WHERE t.oid=%s::regclass""", [REGISTRY])
        row = c.fetchone()
        if row is None or row[0] != REGISTRAR_ROLE or any(row[1:]):
            raise ValueError('Location transition registrar ownership differs')
        c.execute('SELECT record FROM '+REGISTRY+' WHERE singleton IS TRUE')
        rows = c.fetchall()
        if len(rows) != 1:
            raise ValueError('Location transition requires one immutable registration')
        value = rows[0][0]
        return json.loads(value) if isinstance(value,str) else value


def _bundle(record):
    """Full retained archive and installed source roster, with exact hashes."""
    directory = Path(os.environ.get('VF_MTA_LOCATION_TRANSITION_BUNDLE', ''))
    if not directory.is_absolute():
        raise ValueError('Location transition requires its reviewed absolute bundle')
    blobs = {}
    for name in ('old-manifest.json', 'old-source.zip', 'new-manifest.json'):
        raw = (directory/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['bundle'][name]:
            raise ValueError('Location transition bundle identity differs: '+name)
        blobs[name] = raw
    old = json.loads(blobs['old-manifest.json'])
    new = json.loads(blobs['new-manifest.json'])
    with ZipFile(directory/'old-source.zip') as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(old['files']):
            raise ValueError('Location transition old archive roster differs')
        for name in names:
            if hashlib.sha256(archive.read(name)).hexdigest() != old['files'][name]:
                raise ValueError('Location transition old archive file differs: '+name)
    if (old['archive_sha256'] != record['bundle']['old-source.zip']
            or old['native_adapter_digest'] != record['old_adapter_digest']
            or old['implementation_digest'] != record['implementation_digest']):
        raise ValueError('Location transition old manifest identities differ')
    from mta.mdm.production_families import legacy_adapter_paths, adapter_digest
    old_adapter = digest({name: old['files']['mta/'+name] for name in legacy_adapter_paths()})
    if old_adapter != record['old_adapter_digest']:
        raise ValueError('Location transition original adapter reconstruction differs')
    installed = source_files()
    if (set(new) != {'files'} or new['files'] != installed
            or digest(installed) != record['new_source_manifest_digest']
            or adapter_digest() != record['new_adapter_digest']):
        raise ValueError('Location transition installed source manifest differs')


def validate_record(record, source, initialization, *, files=True):
    from mta.mdm.initialization import implementation_digest
    from mta.runtime.models import CalculationRun
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    expected_keys = {'transition_id', 'version', 'database_oid', 'database_name',
        'namespace_registration_id', 'source_id', 'source_digest', 'initialization_id',
        'initialization_receipt_digest', 'configuration_digest', 'implementation_digest',
        'old_adapter_digest', 'old_integration_digest', 'new_adapter_digest',
        'new_source_manifest_digest', 'first_day', 'last_day', 'predecessor_id',
        'predecessor_output_digest', 'old_prefix', 'bundle', 'review_evidence'}
    if set(record) != expected_keys or record['version'] != VERSION:
        raise ValueError('Location transition record fields/version differ')
    uuid.UUID(record['transition_id'])
    with connection.cursor() as c:
        c.execute("SELECT d.oid::bigint,d.datname,r.registration_id::text "
            "FROM pg_database d CROSS JOIN fresh_control.owned_namespace r "
            "WHERE d.datname=current_database() AND r.singleton IS TRUE")
        database = c.fetchone()
    if (database != (record['database_oid'], record['database_name'], record['namespace_registration_id'])
            or record['source_id'] != source.pk or record['source_digest'] != source.digest
            or record['initialization_id'] != str(initialization.pk)
            or record['initialization_receipt_digest'] != initialization.receipt_digest
            or record['configuration_digest'] != initialization.configuration_digest
            or record['implementation_digest'] != initialization.implementation_digest
            or record['implementation_digest'] != implementation_digest()):
        raise ValueError('Location transition source/initialization identity differs')
    first, last = date.fromisoformat(record['first_day']), date.fromisoformat(record['last_day'])
    prefix = record['old_prefix']
    if (not prefix or first > last or len(prefix) != len({r['run_id'] for r in prefix})
            or set(record['bundle']) != {'old-manifest.json','old-source.zip','new-manifest.json'}
            or not record['review_evidence']):
        raise ValueError('Location transition finite boundary/evidence differs')
    parent = None
    for node in prefix:
        if set(node) != {'run_id','output_digest','business_date'}:
            raise ValueError('Location transition prefix fields differ')
        run = CalculationRun.objects.get(pk=node['run_id'])
        if (run.status != 'SUCCEEDED' or run.kind != 'DAILY_CHAIN'
                or run.predecessor_id != parent or run.output_digest != node['output_digest']
                or run.business_date.isoformat() != node['business_date'] or run.business_date >= first
                or not MdmDailyInputCapture.objects.filter(run=run,source=source,status='CONSUMED').exists()):
            raise ValueError('Location transition accepted prefix differs')
        parent = run.pk
    if (str(parent) != record['predecessor_id']
            or prefix[-1]['output_digest'] != record['predecessor_output_digest']):
        raise ValueError('Location transition predecessor differs')
    if files:
        _bundle(record)
    return record


def integration_identity(source, initialization, seal):
    """Identity used to reconstruct the original immutable integration seal."""
    from mta.mdm.production_families import adapter_digest
    if seal.receipt.get('closing_projection_version') == VERSION:
        identity = dict(adapter_digest=adapter_digest(), closing_projection_version=VERSION,
                        source_manifest_digest=source_manifest_digest())
        if identity != {key: seal.receipt.get(key) for key in identity}:
            from mta.mdm.presentation_compatibility import require_exact_presentation_delta
            return require_exact_presentation_delta(source, initialization, seal, identity)
        return identity
    if 'closing_projection_version' in seal.receipt:
        raise ValueError('Unknown native closing projection version')
    record = registration()
    if record is None:
        raise ValueError('Changed native adapter requires the exact registered location transition')
    validate_record(record, source, initialization)
    if (record['old_adapter_digest'] != seal.receipt.get('adapter_digest')
            or record['old_integration_digest'] != seal.digest):
        raise ValueError('Location transition original integration seal differs')
    return dict(adapter_digest=record['old_adapter_digest'])


def run_identity(run, source):
    """Classify from an original seal or explicit prefix, never missing receipts."""
    from mta.runtime.mdm_integration_models import MdmSourceIntegration
    seal = MdmSourceIntegration.objects.get(source=source)
    version = seal.receipt.get('closing_projection_version')
    if version == VERSION:
        return dict(version=VERSION, transition_id=None, source_digest=source.digest,
            adapter_digest=seal.receipt['adapter_digest'], integration_digest=seal.digest,
            source_manifest_digest=seal.receipt['source_manifest_digest'])
    if version is not None:
        raise ValueError('Unknown native closing projection version')
    record = registration()
    if record is None:
        return dict(version=V1)
    if (source.pk != record['source_id'] or source.digest != record['source_digest']
            or seal.digest != record['old_integration_digest']):
        raise ValueError('Location transition run source differs')
    old = {p['run_id']:p for p in record['old_prefix']}
    if str(run.pk) in old:
        if (run.output_digest != old[str(run.pk)]['output_digest']
                or run.business_date.isoformat() != old[str(run.pk)]['business_date']):
            raise ValueError('Location transition old run identity differs')
        return dict(version=V1)
    if not date.fromisoformat(record['first_day']) <= run.business_date <= date.fromisoformat(record['last_day']):
        raise ValueError('Location transition run lies outside its exact boundary')
    return dict(version=VERSION, transition_id=uuid.UUID(record['transition_id']),
        source_digest=source.digest, integration_digest=seal.digest, adapter_digest=record['new_adapter_digest'],
        source_manifest_digest=record['new_source_manifest_digest'])


def admit(source, business_date, parent):
    """Exact first predecessor or a same-transition descendant, before execute_day."""
    from mta.runtime.mdm_integration_models import MdmSourceIntegration
    seal = MdmSourceIntegration.objects.get(source=source)
    if parent is not None and (parent.status != 'SUCCEEDED' or parent.kind != 'DAILY_CHAIN'):
        raise ValueError('Closing projection requires a successful daily predecessor')
    if seal.receipt.get('closing_projection_version') == VERSION:
        if parent is not None:
            verified_receipt(parent, source)
        return
    record = registration()
    if record is None:
        raise ValueError('Location transition registration is required')
    day = date.fromisoformat(str(business_date))
    if parent is None or not date.fromisoformat(record['first_day']) <= day <= date.fromisoformat(record['last_day']):
        raise ValueError('Location transition effective day differs')
    if day == date.fromisoformat(record['first_day']):
        if (str(parent.pk) != record['predecessor_id']
                or parent.output_digest != record['predecessor_output_digest']):
            raise ValueError('Location transition first predecessor differs')
    else:
        receipt = verified_receipt(parent, source)
        if receipt is None or str(receipt.transition_id) != record['transition_id']:
            raise ValueError('Location transition successor predecessor differs')


def capture_identity(capture):
    values = {f.attname:getattr(capture,f.attname) for f in capture._meta.fields
        if f.name not in ('captured_at','consumed_at','status')}
    return digest({key:str(value) if isinstance(value,uuid.UUID) else value
                   for key,value in values.items()})


def verified_receipt(run, source):
    from mta.runtime.mdm_projection_models import MdmClosingProjectionReceipt
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    expected = run_identity(run, source)
    if expected['version'] == V1:
        # Read-only pre-upgrade checks of explicitly v1 runs need no v2 table.
        # Classification above came from the immutable seal/prefix, not absence.
        with connection.cursor() as c:
            c.execute("SELECT to_regclass('mta.fresh_mta_mdmclosingprojectionreceipt')")
            installed = c.fetchone()[0] is not None
        if installed and MdmClosingProjectionReceipt.objects.filter(run=run).exists():
            raise ValueError('Original v1 run must not acquire a v2 projection receipt')
        return None
    receipt = MdmClosingProjectionReceipt.objects.filter(run=run).first()
    capture = MdmDailyInputCapture.objects.get(run=run,source=source,status='CONSUMED')
    if (receipt is None or receipt.status != 'SEALED'
            or any(getattr(receipt,k) != v for k,v in expected.items())
            or receipt.capture_digest != capture_identity(capture)
            or receipt.digest != digest(receipt.metadata)
            or set(receipt.metadata) != {'version','partitions','sources'}
            or receipt.metadata['version'] != VERSION):
        raise ValueError('Native closing projection receipt is missing or differs')
    return receipt
