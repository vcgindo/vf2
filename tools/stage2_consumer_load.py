"""Map the frozen Stage 2 staging rows into existing typed consumer tables.

This artifact is deliberately NOT admitted for serving: native Demo hierarchy
has no membership in the unchanged authorized permission catalogue. No engine
success, parity receipt, command, or serving configuration is created.
"""
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.stage2_dataset_load import DATA, DB, IDENTITY, quote, encoded

RUN = uuid.UUID('f9db3dfc-efc3-488d-af2f-a88e8b2c68ee')
PREFIXES = ('closing/importer/', 'closing/dbm/', 'closing/btr/',
            'closing/consumer_context/', 'closing/orders/', 'reports/bpr/')
RENAMES = dict(sku_code='SKUCode',location_code='WhCode',parent_location_code='ParentWhCode',
    to_black='TOR_B',to_red='TOR_R',to_yellow='TOY',to_green='TOG',to_blue='TOBlue')
PROJECTIONS = dict(PickBand='vf_PickListReport',PickPostRow='vf_PickListReport',
    ExcessInventoryRow='ExcessInventoryDetails',FulfillmentSummaryRow='OrderFulfillmentData',
    FulfillmentDetailRow='OrderFulfillmentDataDetails',ExpediteRow='ExpediteDispatches')


def main():
    from tools.stage2_dataset import require_reconciled_source
    require_reconciled_source()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
    import django
    django.setup()
    from django.db import connection, transaction
    from mta.runtime import models
    from mta.runtime.relational_state import CATALOG, save_image, load_image, table_sql
    from mta.serialization import storage, digest
    if connection.settings_dict['NAME'] != DB: raise ValueError('Owned isolated DB required')
    manifest=json.loads((DATA/'dataset-manifest.json').read_text())
    source_tables={(s['source'].split('_')[1],t['table_name'].casefold()):(s,t)
        for s in manifest['sources'] for t in s['tables'] if 'exclusion' not in t}
    mapping=dict(identity=IDENTITY,run_id=str(RUN),status='BLOCKED_PERMISSION_MEMBERSHIP',images=[],projections=[],gaps=[])

    def rows(role,name):
        source,table=source_tables[(role,name.casefold())]
        schema='stage_'+source['source'].lower()
        with connection.cursor() as cur:
            cur.execute('SELECT '+','.join(quote(c['name']) for c in table['columns'])+' FROM '+quote(schema)+'.'+quote(table['schema_name']+'__'+table['table_name'])+' ORDER BY vf_source_ordinal')
            return table,[dict(zip([c['name'] for c in table['columns']],r)) for r in cur.fetchall()]

    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute('SELECT identity FROM stage2_owner.identity')
            if cur.fetchall()!=[(IDENTITY,)]: raise ValueError('Staging ownership differs')
        payload=dict(origin='legacy-derived-ui-fixture',dataset=IDENTITY)
        existing=models.CalculationRun.objects.filter(pk=RUN).first()
        if existing:
            if existing.kind!='LEGACY_UI_FIXTURE' or existing.status!='FIXTURE_BLOCKED' or existing.input_payload!=payload:
                raise ValueError('Fixture identity mismatch')
            mapping=json.loads((DATA/'mapping.json').read_text())
            for item in mapping['images']: load_image(existing,item['metadata'])
            for item in mapping['projections']:
                model=getattr(models,item['model'])
                got=list(model.objects.filter(run=existing).order_by('ordinal').values(*item['fields']))
                if digest(storage(got))!=item['digest']: raise ValueError('Projection retry drift')
            print('Existing blocked fixture verified without mutation',flush=True)
            return
        if models.CalculationRun.objects.exists(): raise ValueError('Dataset database contains unrelated calculation runs')
        run=models.CalculationRun.objects.create(id=RUN,kind='LEGACY_UI_FIXTURE',status='FIXTURE_BLOCKED',
            input_payload=payload,input_digest=digest(payload),execution_revision='stage2-source-load-v1',business_date='2025-10-08')
        for path,(role,name) in CATALOG['bindings'].items():
            if not path.startswith(PREFIXES): continue
            if (role,name.casefold()) not in source_tables:
                mapping['gaps'].append(dict(binding=path,reason='source_table_absent'));continue
            table,source_rows=rows(role,name)
            target_columns=CATALOG['tables'][role+'/'+name]
            source_names={c['name'].casefold():c['name'] for c in table['columns']}
            absent=[n for n,k in target_columns if n.casefold() not in source_names]
            # Missing target columns are not filled with invented NULL/defaults.
            selected=[(source_names[n.casefold()],n,k) for n,k in target_columns if n.casefold() in source_names]
            wire=storage([{target:r[source] for source,target,k in selected} for r in source_rows])
            metadata=save_image(run,path,path,wire)
            if load_image(run,metadata)!=wire: raise ValueError('Consumer full-value readback differs '+path)
            mapping['images'].append(dict(binding=path,source=f'Demo_{role}_1.dbo.{name}',
                target=table_sql(role+'/'+name),columns=[dict(source=s,target=n,type=k) for s,n,k in selected],
                source_only_columns=[c['name'] for c in table['columns'] if c['name'].casefold() not in {n.casefold() for n,k in target_columns}],
                absent_target_columns=absent,metadata=metadata))
            if absent: mapping['gaps'].append(dict(binding=path,reason='target_columns_absent_in_source',columns=absent))
        for model_name,source_name in PROJECTIONS.items():
            model=getattr(models,model_name)
            fields=[f.name for f in model._meta.fields if f.name not in ('id','run','ordinal')]
            table,source_rows=rows('BPR',source_name)
            source_names={c['name'].casefold():c['name'] for c in table['columns']}
            pairs=[(source_names[RENAMES.get(f,f).casefold()],f) for f in fields]
            expected=[{f:r[s] for s,f in pairs} for r in source_rows]
            # bulk_create writes only existing consumer columns; no producer is called.
            model.objects.bulk_create([model(run=run,ordinal=i,**r) for i,r in enumerate(expected)],batch_size=500)
            actual=list(model.objects.filter(run=run).order_by('ordinal').values(*fields))
            if storage(actual)!=storage(expected): raise ValueError('Projection full-value readback differs '+model_name)
            mapping['projections'].append(dict(model=model_name,source='Demo_BPR_1.dbo.'+source_name,
                target=model._meta.db_table,columns=[dict(source=s,target=f) for s,f in pairs],
                fields=fields,count=len(expected),digest=digest(storage(actual))))
        if run.checkpoints.exists() or run.commands.exists() or run.parity_summary or run.production_manifest:
            raise ValueError('Fixture must not claim a calculated publication')
    (DATA/'mapping.json').write_text(json.dumps(mapping,indent=2))
    print('Mapped',len(mapping['images']),'images and',len(mapping['projections']),'projection families; fixture remains blocked',flush=True)


if __name__=='__main__':main()
