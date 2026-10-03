"""Consolidate the bounded dataset proof; never grant fixture admission."""
import csv
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.stage2_vm_contract import atomic,sealed,roster
from tools.stage2_vm_load import DATA,DB,IDENTITY
from tools.stage2_vm_dataset import sha
from tools.stage2_vm_consumer_load import RUN


def main(*,window='fixture-window-001'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
    import django
    django.setup()
    from django.db import connection
    from django.test import override_settings
    from mta.runtime.models import CalculationRun
    from mta.presentation.context import selected_run,PublicationUnavailable
    from mta.serialization import digest
    if connection.settings_dict['NAME']!=DB:raise ValueError('Wrong database')
    manifest,manifest_sha=sealed(DATA)
    staging=json.loads((DATA/'staging-validation.json').read_text())
    mapping=json.loads((DATA/'mapping.json').read_text())
    if staging['status']!='STAGING_VERIFIED' or staging['manifest_sha256']!=manifest_sha:raise ValueError('Staging proof incomplete')
    if mapping['manifest_sha256']!=manifest_sha or mapping['gaps']:raise ValueError('Consumer mappings incomplete')
    expected={s['source']+'.'+t['schema_name']+'.'+t['table_name'] for s,t in roster(manifest).values()}
    if len(mapping['exports'])!=len(expected) or {t['source'] for t in mapping['exports']}!=expected:raise ValueError('Export disposition incomplete')
    images=mapping['images'];projections=mapping['projections']
    receipts={i['binding']:i['metadata'] for i in images}
    receipts.update({'projection/'+p['model']:{k:p[k] for k in ('model','count','digest','fields','wire','provenance')} for p in projections})
    with connection.cursor() as cur:
        cur.execute('SELECT manifest_sha256 FROM stage2_owner.manifest')
        if cur.fetchall()!=[(manifest_sha,)]:raise ValueError('Ownership seal differs')
        cur.execute('SELECT binding,metadata FROM stage2_owner.consumer_receipts')
        actual={k:json.loads(v) if isinstance(v,str) else v for k,v in cur.fetchall()}
        if actual!=receipts:raise ValueError('Consumer receipt roster differs')
    run=CalculationRun.objects.get(pk=RUN)
    if CalculationRun.objects.count()!=1 or run.kind!='LEGACY_UI_FIXTURE' or run.status!='FIXTURE_BLOCKED':raise ValueError('Unrelated/incorrect fixture state')
    payload=dict(origin='human-supplied-original-vm-backups',dataset=IDENTITY,manifest_sha256=manifest_sha)
    if run.input_payload!=payload or run.input_digest!=digest(payload):raise ValueError('Run input changed')
    if (run.output_digest or run.production_digest or run.production_manifest or run.parity_summary or run.output_roster or run.failure or run.opening_key or run.predecessor_id or run.completed_at or run.checkpoints.exists() or run.commands.exists()):raise ValueError('Fixture falsely claims engine/workflow state')
    with override_settings(VF_MTA_PUBLISHED_RUN=str(RUN),VF_MTA_PUBLISHED_DIGEST=manifest_sha):
        try:selected_run()
        except PublicationUnavailable as exc:
            denial=str(exc)
            if denial!='publication_identity_or_status_mismatch':raise
        else:raise ValueError('Fixture was unexpectedly admitted')
    inventory=ROOT/'docs/audit-2026-10-01/PAGE_INTERACTION_INVENTORY.csv'
    if sha(inventory)!=manifest['inventory_sha256']:raise ValueError('Page inventory changed')
    pages={'P09':['Importer','BPR'],'P10':['Importer','BPR','BTR'],'P15':['Importer','BPR','BTR','DBM'],
        'P16':['Importer','BPR'],'P21':['Importer','BPR','BTR','DBM'],'P22':['Importer','BTR'],
        'P23':['Importer','BPR'],'P24':['Importer','BTR'],'P25':['Importer','DBM']}
    inventory_rows=list(csv.DictReader(inventory.open(encoding='utf-8-sig')))
    coverage=[]
    proof=json.loads((DATA/window/'authenticated-fixture-proof.json').read_text())
    restoration=json.loads((DATA/window/'window-restoration.json').read_text())
    if restoration['status']!='PASS':raise ValueError('Restoration proof incomplete')
    observed={(o['actor'],o['route']):o for o in proof['observations']}
    required={('broad','GetLastRunDate'):200,('broad','DBMDataCount'):200,
        ('restricted','DBMDataCount'):200,('broad','DBMData'):200,('restricted','DBMData'):200,
        ('restricted-forged-body','DBMDataCount'):200,('restricted','DailyDataGraph'):200,
        ('broad','DBMApplySelectedNorms'):403,('broad','DBMUpdateSleepTbl'):403,
        ('normal-preview-denied','DBMDataCount'):403}
    if any(observed.get(key,{}).get('status')!=status for key,status in required.items()):raise ValueError('Representative boundary proof incomplete')
    if not 0<proof['counts']['restricted']<proof['counts']['broad']:raise ValueError('Scope proof incomplete')
    if int(observed[('restricted-forged-body','DBMDataCount')]['body']['recordCount'])!=proof['counts']['restricted']:raise ValueError('Forged scope changed result')
    blocked=proof['status']=='FAILED'
    if blocked:
        failure=proof['observations'][-1]
        if failure['route']!='RRRDataCount' or failure['status']!=504:raise ValueError('Unconsolidated additional failure')
    elif proof['status']!='PASS_REPRESENTATIVE_AUTHENTICATED_FIXTURE':raise ValueError('Unknown authenticated proof status')
    integrity=json.loads((DATA/'fixture-integrity.json').read_text())
    indexes=json.loads((DATA/'fixture-indexes.json').read_text())
    if indexes['status']!='PASS' or indexes['manifest_sha256']!=manifest_sha or len(indexes['indexes'])!=3:raise ValueError('Fixture history indexes unverified')
    disabled=json.loads((DATA/window/'disabled-login-proof.json').read_text())
    if integrity['status']!='PASS' or not integrity['immutable_zero_row_statement_denied']:raise ValueError('Fixture integrity proof incomplete')
    if len(disabled)!=2 or not all(item['login_denied'] and item['status'] in (400,401,403) for item in disabled):raise ValueError('Fixture actor disable proof incomplete')
    for page,roles in pages.items():
        entries=[r for r in inventory_rows if r['page']==page]
        coverage.append(dict(page=page,routes=[r['contract'] for r in entries if r['kind']=='route'],
            retained_inventory_contracts=len(entries),source_roles=roles,
            data_status='MAPPED_SOURCE_COVERAGE',authenticated_api_status='REPRESENTATIVE_READ_PROVED' if page in (('P25',) if blocked else ('P09','P16','P22','P23','P25')) else 'NOT_ACCEPTED_BY_REPRESENTATIVE_PROOF',
            acceptance='Not page acceptance; no frontend implementation or API value parity claimed'))
    scope=json.loads((DATA/'permission-compatibility.json').read_text())
    if set(scope)!={'Importer','BPR','BTR','DBM'} or any(v['matched_codes'] for role in scope.values() for v in role.values()):raise ValueError('Scope blocker evidence changed; reassess')
    evidence_names=['manifest-seal.json','staging-validation.json','mapping.json','relationships.json','source-consistency.json',
        'permission-compatibility.json','actor-scope-mismatch.json','dbm-history-coverage.json','projection-preflight.json',
        'ui-metadata-preflight.json','dbm-capture-reconciliation.json','schema-proof.txt','consumer-retry-validation.json',
        'fixture-integrity.json','fixture-indexes.json','code-proof.json',window+'/disabled-login-proof.json']
    relationships=json.loads((DATA/'relationships.json').read_text())
    result=dict(identity=IDENTITY,status='BLOCKED_CONSUMER_READINESS' if blocked else 'DATASET_READY_WITH_DECLARED_API_GAPS',manifest_sha256=manifest_sha,
        dataset_ready=not blocked,
        blockers=[dict(route='RRRDataCount',status=504,seconds=failure['seconds'],
            reason='Existing full-native-population consumer exceeds unchanged60-second gateway limit',
            next_boundary='Separate bounded RRR reader diagnosis/correction and fresh authenticated/restoration proof; no frontend work',
            unexecuted=['RRRData','GetBTRData','GetPlanningDataGridCount','GetPlanningDataGrid'])] if blocked else [],
        run_id=str(RUN),business_date=str(run.business_date),database=DB,
        staging=dict(tables=len(expected),rows=sum(t['count'] for s,t in roster(manifest).values()),proof='Full ordered typed value digest, NULL vector, ordinal and count readback'),
        consumer=dict(images=len(images),projections=len(projections),image_rows=sum(i['metadata']['count'] for i in images),
            projection_rows=sum(p['count'] for p in projections),proof='Manifest-bound source and complete mapped target digests; transactional inserts'),
        coverage=coverage,optional_roles_not_supplied=manifest['optional_roles_not_supplied'],
        source_relationships=dict(importer_bpr_key_bag_differences=len(relationships['importer_master_vs_bpr_key_bag']),
            bpr_btr_key_bag_differences=len(relationships['bpr_vs_btr_key_bag']),disposition='Native historical/current population differences preserved; no repair or parity claim'),
        scope=dict(original_preview_membership='Zero native memberships; existing grants unchanged',resolution='Expressly authorized new fixture-only native-scope actors',
            counts=proof['counts'],accounts_disabled_after_proof=True),
        serving=dict(implemented=True,normal_production_denial=denial,window=window,restoration='PASS',
            identity='LEGACY_UI_FIXTURE/FIXTURE_BLOCKED; no engine success or parity',selection='Pinned fixture-serving.json and dedicated native permission catalogue'),
        declared_api_gaps=['GetResearchInsightData and GetHistroricalAvailabilityBPRData still require production full-output adapters; fixture returns503',
            'GetBPRData/GetBPRDataCount/GetAnalyticsData and GetRemarkDetails require native ancillary adapters; terminal June17 exceptions are not transferred',
            'AvailabilityTrend/AvailabilityAgeing require bounded BTR daily-history reads; eager reads over one million rows fail closed',
            'Planning overview/GIT and Guided Excess retain production-only ancillary/history contracts; no positive logistics or workflow acceptance',
            'Native AdminBPR metadata differs in39 columns from retained static UI config; data preserved, no UI parity claim'],
        excluded=dict(engine_execution=False,accepted_f1_f2_changes=False,existing_authentication_grant_changes=False,page_implementation=False,stage3_5=False),
        evidence={name:sha(DATA/name) for name in evidence_names+['consumer-publication.json','freeze-receipt.json','fixture-serving.json','fixture-permissions.json',window+'/authenticated-fixture-proof.json',window+'/window-restoration.json']})
    atomic(DATA/'dataset-validation.json',result)
    print(json.dumps({k:result[k] for k in ('status','staging','consumer','scope')},indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--window',default='fixture-window-001')
    main(window=parser.parse_args().window)
