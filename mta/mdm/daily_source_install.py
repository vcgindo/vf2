"""Install retained synthetic master owners once in the exclusively owned shell.

Importer/DBM/BTR bags come from their registered opening JSON paths. The BPR
metadata owner uses the canonical 01.ImportData full-copy statements. No engine
outputs, old workflows, credentials or April fixture rows are imported.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from django.db import connection, transaction

from mta.mdm.daily_source import (SCHEMA, ARTIFACT_SHA, APPROVAL_DAY_ARTIFACT_SHA,
                                  adapter_digest, configuration_digest, require_binding)
from mta.mdm.owned_namespace import authorize_install
from mta.mdm.source import DLL
from mta.runtime import mdm_models as models
from mta.runtime import mdm_skuloc_models as pairs
from mta.serialization import digest, storage

BPR_COPY_SHA = 'c248baeedda13d74a71a499c8b59b7ec46f05f11db00938de59a746bce94ce93'
IL_SHA = 'ccd47dc8d76895a6aa63ad5d6beaadb32f4f53ab75047a68fb8055382fd87ca1'


def registered(raw, expected):
    if expected not in (ARTIFACT_SHA, APPROVAL_DAY_ARTIFACT_SHA):
        raise ValueError('This bootstrap requires an exact registered MDM artifact')
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Synthetic master artifact bytes differ')
    manifest=json.loads((Path(__file__).resolve().parents[2]/'baseline/manifest.json').read_text())
    if expected not in {row['sha256'] for row in manifest['retained_resources']}:
        raise ValueError('Synthetic master artifact is not registered')
    artifact=json.loads(raw)
    if artifact.get('schema') != 'block3-sizeable-input-v1':
        raise ValueError('Unsupported retained synthetic master schema')
    return artifact


from mta.mdm.master_owners import business_fields, typed, owner_batches


def owners(artifact):
    return owner_batches(artifact['case']['opening'])


@transaction.atomic
def install(raw, expected):
    namespace=authorize_install(expected,adapter_digest())
    database=namespace['database_name']
    artifact=registered(raw,expected); batches=owners(artifact)
    # A new shell has no workflows. Never reinterpret an existing source as a
    # fresh owner or overwrite its current rows/queued tasks.
    if models.MdmSource.objects.exists():
        raise ValueError('Synthetic master source already exists; reset is prohibited')
    families={str(i):dict(owners=[]) for i in (1,2,3)}
    for family,model,kwargs,rows,path in batches:
        families[str(family)]['owners'].append(dict(model=model.__name__,**kwargs,
            input_path=path,rows=len(rows),digest=digest(storage(rows)),
            fields=[f.name for f in business_fields(model)]))
    receipt=dict(schema=SCHEMA,artifact_sha256=expected,artifact_schema=artifact['schema'],
        adapter_sha256=adapter_digest(),families=families,database=database,
        opening_date=artifact['case']['opening_date'],
        canonical=dict(dll=DLL,bpr_metadata_copy=BPR_COPY_SHA,mdm_use_queries_il=IL_SHA),
        configuration=configuration_digest(),
        initial_workflows='new isolated owner; no pre-existing tasks, drafts, requests or remarks')
    if namespace['registration'] is not None:
        receipt['owned_namespace']=namespace['registration']
    source=models.MdmSource.objects.create(digest=digest(receipt),dll_digest=DLL,
        database_name=database,receipt=receipt)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.mdm_current_bootstrap',%s,true)", [str(source.pk)])
    for family,model,kwargs,rows,path in batches:
        model.objects.bulk_create([model(source=source,ordinal=i,**kwargs,**row)
            for i,row in enumerate(rows,1)],batch_size=500)
        actual=list(model.objects.filter(source=source,**kwargs).order_by('ordinal')
                    .values(*[f.name for f in business_fields(model)]))
        if storage(actual) != storage(rows):raise ValueError('Synthetic owner typed readback differs: '+path)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.mdm_current_bootstrap','',true)")
    for master_id in (2,3):
        item=families[str(master_id)]
        models.MdmFamilySource.objects.create(source=source,master_id=master_id,
            digest=digest(item),receipt=item)
    provenance=dict(schema='fresh-shell-workflow-opening-v1',artifact_sha256=expected,
                    mdm_source_digest=source.digest,opening_date=artifact['case']['opening_date'])
    from mta.mdm.daily_input import install_pair_exclusions
    install_pair_exclusions(source,deepcopy(artifact['case']['static_day']['exclusions']),
        provenance={**provenance,'input_path':'/case/static_day/exclusions'})
    from mta.presentation.daily_requests import initialize
    initialize([],provenance={**provenance,'reason':'New isolated shell; no request workflow events exist'})
    from mta.presentation.ancillary_live import BPR, initialize_owner
    remark={**provenance,'reason':'New isolated shell; no BPR remark workflow events exist'}
    initialize_owner(BPR,provenance_digest=digest(remark),provenance_receipt=remark)
    require_binding(source,artifact_sha256=expected,artifact_schema=artifact['schema'])
    return source
