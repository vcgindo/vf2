"""New named workflow owner for a registered offline scenario, never a reset."""
import re
from copy import deepcopy
from django.db import connection, transaction
from mta.mdm.daily_source import SCHEMA, adapter_digest, configuration_digest, require_binding
from mta.mdm.daily_source_install import owners, business_fields, BPR_COPY_SHA, IL_SHA
from mta.mdm.source import DLL
from mta.runtime import mdm_models as models
from mta.runtime.offline_scenario import admit
from mta.serialization import digest, storage


@transaction.atomic
def install(raw, expected, owner):
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,39}', owner):
        raise ValueError('Explicit bounded offline owner required')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        database = cursor.fetchone()[0]
    if database != 'daily_3006':
        raise ValueError('Offline source requires owned daily_3006')
    # Serialize only this source identity. Other sources and workflow owners
    # remain present, unmodified and independently scoped.
    lock = int.from_bytes(__import__('hashlib').sha256(owner.encode()).digest()[:8],'big',signed=True)
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(%s)',[lock])
    artifact = admit(raw,expected); batches = owners(artifact)
    families = {str(i):dict(owners=[]) for i in (1,2,3)}
    for family,model,kwargs,rows,path in batches:
        families[str(family)]['owners'].append(dict(model=model.__name__,**kwargs,
            input_path=path,rows=len(rows),digest=digest(storage(rows)),
            fields=[f.name for f in business_fields(model)]))
    receipt = dict(schema=SCHEMA,artifact_sha256=expected,artifact_schema=artifact['schema'],
        adapter_sha256=adapter_digest(),families=families,database=database,
        opening_date=artifact['case']['opening_date'],offline_owner=owner,
        scenario_sha256=artifact['scenario_sha256'],
        canonical=dict(dll=DLL,bpr_metadata_copy=BPR_COPY_SHA,mdm_use_queries_il=IL_SHA),
        configuration=configuration_digest(),initial_workflows='new separately scoped offline owner')
    existing = models.MdmSource.objects.filter(receipt__offline_owner=owner).first()
    if existing:
        if existing.receipt != receipt or existing.digest != digest(receipt):
            raise ValueError('Existing offline owner pins differ; never reset')
        return require_binding(existing,artifact_sha256=expected,artifact_schema=artifact['schema'])
    source = models.MdmSource.objects.create(digest=digest(receipt),dll_digest=DLL,
        database_name=database,receipt=receipt)
    for family,model,kwargs,rows,path in batches:
        model.objects.bulk_create([model(source=source,ordinal=i,**kwargs,**row)
            for i,row in enumerate(rows,1)],batch_size=500)
        actual = list(model.objects.filter(source=source,**kwargs).order_by('ordinal')
            .values(*[f.name for f in business_fields(model)]))
        if storage(actual)!=storage(rows):
            raise ValueError('Offline master readback differs: '+path)
    for master_id in (2,3):
        models.MdmFamilySource.objects.create(source=source,master_id=master_id,
            digest=digest(families[str(master_id)]),receipt=families[str(master_id)])
    from mta.mdm.daily_input import install_pair_exclusions
    install_pair_exclusions(source,deepcopy(artifact['case']['static_day']['exclusions']),
        provenance=dict(schema='fresh-offline-exclusions-v1',owner=owner,artifact_sha256=expected,
                        input_path='/case/static_day/exclusions'))
    # Existing application-owned request/remark populations are captured by
    # execute_day. Installing a timeline must never clear or reinitialize them.
    return require_binding(source,artifact_sha256=expected,artifact_schema=artifact['schema'])
