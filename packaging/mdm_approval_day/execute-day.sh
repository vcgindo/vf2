#!/usr/bin/env bash
# One approved date per bounded worker. Never loop, retry or select serving state.
set -euo pipefail
INDEX="${1:?day index 0, 1 or 2 required}"
case "$INDEX" in 0|1|2) ;; *) exit 2 ;; esac
export INDEX
python - <<'PY'
import hashlib,json,os,pathlib
p=pathlib.Path('/request/execution-request.json')
expected=os.environ.get('MDM_DAY_EXECUTION_APPROVAL_SHA256','')
if len(expected)!=64 or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
 raise SystemExit('Exact execution approval absent; no day may run')
r=json.loads(p.read_text())
assert r['database']=='fresh_mdm_approval_day_20261010_002'
assert r['maximum_business_day_calls']==3 and r['dates']==['2026-06-06','2026-06-07','2026-06-08']
assert r['serving_changes'] is False
for name,sha in r['request_files'].items():
 assert pathlib.Path(name).name==name
 assert hashlib.sha256((p.parent/name).read_bytes()).hexdigest()==sha,name
PY

export EVIDENCE_ROOT="/execution/day${INDEX}"
export VF_EVIDENCE_ROOT="$EVIDENCE_ROOT"
# Exclusive directory is the one-shot boundary, including failed calculations.
mkdir "$EVIDENCE_ROOT"
mkdir "$EVIDENCE_ROOT/pick"
exec 2> >(tee -a "$EVIDENCE_ROOT/stderr.log" >&2)
trap 'echo "STOP: preserve this attempt; do not rerun this day command" >&2' ERR
export DJANGO_SETTINGS_MODULE=tools.mdm_approval_day_settings
export VF_MDM_SOURCE_DIGEST=39f76f9c718a28e014737e8c856af7d29f1ab5dbdfd2370321a6cb539d010f8e
export VF_MDM_APPROVAL_HIERARCHY_FILE=/request/mdm-hierarchy.json
export VF_MTA_DAILY_PUBLICATION=1 VF_MTA_SYNTHETIC_ROSTER=core-without-bor-v1
export VF_MTA_OPERATIONAL_POLICY=supported-synthetic-active-nms-v1 VF_MTA_ACTIONS_ENABLED=0
export VF_MTA_PUBLISHED_RUN='' VF_MTA_PUBLISHED_DIGEST='' VF_MTA_OPERATIONAL_RECEIPT='' VF_BTR_REPORTING_GENERATION=''
export VF_MTA_CONSUMPTION_POLICY='' VF_MTA_FIXTURE_FILE='' VF_MTA_FIXTURE_SHA256=''
export VF_MTA_TERMINAL_FILE='' VF_MTA_TERMINAL_SHA256='' VF_MTA_EXCESS_HISTORY_FILE='' VF_MTA_EXCESS_HISTORY_SHA256=''
export VF_MTA_PLANNING_EXTENSION='' VF_MTA_RRR_COLOUR_EXTENSION='' VF_MTA_GUIDED_EXCESS_DISPOSITION=''
export VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY=0 VF_MTA_PREACCEPTANCE_FILE='' VF_MTA_PREACCEPTANCE_SHA256=''
export VF_BPR_PREPARED=1 VF_GUIDED_PREPARED=1 VF_RRR_PREPARED=1 VF_HISTORY_REPORTS_PREPARED=1 VF_RESEARCH_AVAILABILITY_PREPARED=1
export VF_MTA_ACTION_TIME_ZONE=Asia/Kolkata
export VF_MTA_PERMISSIONS_FILE=/request/permissions.json
export VF_MTA_PERMISSIONS_SHA256=18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356
export VF_MTA_HIERARCHY_FILE='' VF_MTA_HIERARCHY_SHA256='' VF_MTA_PREDECESSOR_HIERARCHY_FILE=''
export VF_MTA_LOCAL_PERMISSIONS=0
export ARTIFACT=/request/input.json
export ARTIFACT_SHA=be33508fd9e5cd6b0224f02502f61b87a0cfb8cdce44cafb3d1f1c3e1384d847
export FINALIZATION=/request/finalization.json
export FINALIZATION_SHA=c1ae7d95a80d61b32dcd984b24a804d76a45948b23b8187aa90c4a834b83eb5c
export PICK_CONFIG=/request/pick.json
export PICK_CONFIG_SHA=a775176974652ae0c228ab70a11ef4a5cbc2447b6535929397e914cc0e4b1c51
export SHIPMENT=/request/shipment.json
export SHIPMENT_SHA=acffb0bf8164a4a9c6b1017aff52e82c08a9968be1b2e5b4d2c9d432a8e930ce

field() { python -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$1" "$2"; }
sha() { python -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"; }
PREDECESSOR=()
if [ "$INDEX" != 0 ]; then
  PRIOR="/execution/day$((INDEX-1))"
  test -f "$PRIOR/matrix-proof.json"
  python - "$PRIOR" <<'PY'
import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);run=json.loads((p/'run.json').read_text());proof=json.loads((p/'matrix-proof.json').read_text())
assert proof['status']=='PASS' and proof['run_id']==run['run_id'] and proof['output_digest']==run['output_digest']
assert json.loads((p/'accept.json').read_text())['run_id']==run['run_id']
PY
  PREDECESSOR=(--predecessor "$(field "$PRIOR/run.json" run_id)")
  export VF_MTA_HIERARCHY_FILE="$PRIOR/hierarchy.json"
  VF_MTA_HIERARCHY_SHA256="$(sha "$VF_MTA_HIERARCHY_FILE")"; export VF_MTA_HIERARCHY_SHA256
  if [ "$INDEX" = 2 ]; then
    export VF_MTA_PREDECESSOR_HIERARCHY_FILE=/execution/day0/hierarchy.json
  fi
fi

# Fresh source owns exactly the accepted prefix, never a hidden extra attempt.
python - <<'PY' > "$EVIDENCE_ROOT/prefix-check.json"
import django,json,os
django.setup()
from django.db import connection
from mta.runtime.models import CalculationRun
from mta.runtime.mdm_models import MdmSource
from mta.mdm.daily_source import require_root
assert connection.settings_dict['NAME']=='fresh_mdm_approval_day_20261010_002'
source=MdmSource.objects.get(pk=1,digest=os.environ['VF_MDM_SOURCE_DIGEST'])
require_root(source,artifact_sha256=os.environ['ARTIFACT_SHA'],artifact_schema=source.receipt['artifact_schema'])
runs=list(CalculationRun.objects.order_by('business_date'))
assert len(runs)==int(os.environ['INDEX'])
assert all(r.status=='SUCCEEDED' and str(r.business_date)==['2026-06-06','2026-06-07'][i] for i,r in enumerate(runs))
print(json.dumps(dict(existing_calls=len(runs),database=connection.settings_dict['NAME'],source_digest=source.digest)))
PY

# 1. Exactly one production boundary invocation. No automatic retry.
python -m django run_daily "$ARTIFACT" --sha256 "$ARTIFACT_SHA" \
  --day-index "$INDEX" --revision mdm-approval-day-three-date-001 "${PREDECESSOR[@]}" \
  --mdm-source 1 --mdm-source-digest "$VF_MDM_SOURCE_DIGEST" --bpr-remark-horizon 90 \
  --finalization-config "$FINALIZATION" --finalization-config-sha256 "$FINALIZATION_SHA" \
  --complete-pick-policy canonical-tied-order-v1 --pick-output-root "$EVIDENCE_ROOT/pick" \
  --pick-config "$PICK_CONFIG" --pick-config-sha256 "$PICK_CONFIG_SHA" \
  --shipment-input "$SHIPMENT" --shipment-sha256 "$SHIPMENT_SHA" \
  --operational-sources cohort2-operational-sources-v1 \
  --operational-input-sources cohort2-input-tables-v1 \
  --operational-force-sources cohort2-pre-clear-force-v1 > "$EVIDENCE_ROOT/run.json"
RUN="$(field "$EVIDENCE_ROOT/run.json" run_id)"
OUTPUT="$(field "$EVIDENCE_ROOT/run.json" output_digest)"
DATE="$(field "$EVIDENCE_ROOT/run.json" business_date)"
export RUN OUTPUT DATE
if [ "$INDEX" != 0 ]; then
  export VF_MTA_PREDECESSOR_HIERARCHY_FILE="$PRIOR/hierarchy.json"
fi
python - <<'PY'
import json,os,pathlib
r=json.loads((pathlib.Path(os.environ['EVIDENCE_ROOT'])/'run.json').read_text())
assert r['status']=='SUCCEEDED' and r['business_date']==['2026-06-06','2026-06-07','2026-06-08'][int(os.environ['INDEX'])]
PY

# 2. Bind this actual run, then apply the retained authenticated DBM policy.
python -m tools.cohort6_bind_day --template /request/hierarchy-template.json \
  --template-sha256 e3cc38ddae203161c522aacb14e46a1c16c863032e7ad12d619676d84ace3ce9 \
  --run-receipt "$EVIDENCE_ROOT/run.json" --business-date "$DATE" \
  --output "$EVIDENCE_ROOT/hierarchy.json" > "$EVIDENCE_ROOT/hierarchy-receipt.json"
export VF_MTA_HIERARCHY_FILE="$EVIDENCE_ROOT/hierarchy.json"
VF_MTA_HIERARCHY_SHA256="$(sha "$VF_MTA_HIERARCHY_FILE")"; export VF_MTA_HIERARCHY_SHA256
python -m tools.cohort6_actions --run "$RUN" --email-environment NMS_REVIEWER_EMAIL \
  --password-environment NMS_REVIEWER_PASSWORD build-manifest --output "$EVIDENCE_ROOT/actions-manifest.json" \
  --artifact "$ARTIFACT" --artifact-sha256 "$ARTIFACT_SHA" \
  --finalization "$FINALIZATION" --finalization-sha256 "$FINALIZATION_SHA" \
  --pick-config "$PICK_CONFIG" --pick-config-sha256 "$PICK_CONFIG_SHA" \
  --shipment "$SHIPMENT" --shipment-sha256 "$SHIPMENT_SHA" > "$EVIDENCE_ROOT/actions-build.json"
VF_MTA_PREACCEPTANCE_FILE="$EVIDENCE_ROOT/actions-manifest.json" \
VF_MTA_PREACCEPTANCE_SHA256="$(sha "$EVIDENCE_ROOT/actions-manifest.json")" \
python -m tools.cohort6_actions --run "$RUN" --email-environment NMS_REVIEWER_EMAIL \
  --password-environment NMS_REVIEWER_PASSWORD execute > "$EVIDENCE_ROOT/actions.json"

# 3. Existing operational writers and their qualified restore checks.
mkdir "$EVIDENCE_ROOT/operations"
if [ "$INDEX" = 0 ]; then
  python -m django register_cohort6_operational --configuration /request/operations-template.json \
    --sha256 beb072328f16f567cd3a3fffec8a46e1735c319e0e6d3360865eefa428bda3fd \
    --first-run-receipt "$EVIDENCE_ROOT/run.json" > /execution/operation-configuration.json
fi
python - <<'PY'
import json,os,pathlib
i=int(os.environ['INDEX']);root=pathlib.Path(os.environ['EVIDENCE_ROOT'])
v=dict(run_id=os.environ['RUN'],expected_output_digest=os.environ['OUTPUT'],
 configuration_id=json.loads(pathlib.Path('/execution/operation-configuration.json').read_text())['configuration_id'],
 request_key='mdm-approval-day-three-date-001-'+str(i),owned_root=str(root/'operations'))
if i==0:
 opening=json.loads(pathlib.Path('/request/operational-opening.json').read_text());assert set(opening)=={'populations','abort_reasons'}
 v.update(openings=opening['populations'],abort_opening=opening['abort_reasons'])
else:v['predecessor_id']=json.loads(pathlib.Path('/execution/day'+str(i-1)+'/operations.json').read_text())['attempt']
with (root/'operation-request.json').open('x') as f:json.dump(v,f,indent=2)
PY
python -m django cohort2_operational materialize --request "$EVIDENCE_ROOT/operation-request.json" > "$EVIDENCE_ROOT/operations.json"
ATTEMPT="$(field "$EVIDENCE_ROOT/operations.json" attempt)"
python -m django cohort2_operational check --attempt "$ATTEMPT" > "$EVIDENCE_ROOT/operations-check.json"

# 4. Prepare all required native layers before binding read-time access.
VF_MTA_PERMISSIONS_FILE='' VF_MTA_PERMISSIONS_SHA256='' VF_MTA_HIERARCHY_FILE='' VF_MTA_HIERARCHY_SHA256='' \
python - <<'PY' > "$EVIDENCE_ROOT/prepare.json"
import django,json,os
django.setup()
from django.db import connection,transaction
from mta.runtime.models import CalculationRun,DailyUiPublication
from mta.presentation.daily_publication import configuration_identity,source_identity,recipe_identity,prepare_reporting_generation
from mta.presentation.daily_preparation import prepare_layer,verify_layer
run=CalculationRun.objects.get(pk=os.environ['RUN']);assert run.status=='SUCCEEDED' and run.output_digest==os.environ['OUTPUT']
lock=int.from_bytes(run.pk.bytes[:8],'big',signed=True)
with connection.cursor() as c:
 c.execute('SELECT pg_try_advisory_lock(%s)',[lock])
 if not c.fetchone()[0]:raise ValueError('Publication busy')
try:
 identity=dict(output_digest=run.output_digest,source_digest=source_identity(run),configuration_digest=configuration_identity(),recipe_digest=recipe_identity())
 p,_=DailyUiPublication.objects.get_or_create(run=run,defaults=identity)
 assert all(getattr(p,k)==v for k,v in identity.items())
 if p.status=='INCOMPLETE':
  with transaction.atomic():
   with connection.cursor() as c:c.execute("SELECT set_config('fresh.daily_publication_build',%s,true)",[str(run.pk)])
   r=prepare_layer(run,'rrr');verify_layer(run,'rrr',r)
 p,summary=prepare_reporting_generation(run.pk,expected_output_digest=run.output_digest)
 print(json.dumps(dict(run_id=str(run.pk),status=p.status,seal_digest=p.seal_digest,layers=p.layers,
  planning_summary=dict(generation=str(summary.pk),status=summary.status,rows_digest=summary.rows_digest))))
 assert p.status=='READY' and summary.status=='READY'
finally:
 with connection.cursor() as c:c.execute('SELECT pg_advisory_unlock(%s)',[lock])
PY
python -m django accept_daily_operational --run-id "$RUN" --output-digest "$OUTPUT" \
  --attempt "$ATTEMPT" --artifact "$ARTIFACT" --finalization-config "$FINALIZATION" \
  --pick-config "$PICK_CONFIG" --shipment-input "$SHIPMENT" > "$EVIDENCE_ROOT/accept.json"
python -m django check_daily_selection --run-id "$RUN" --output-digest "$OUTPUT" > "$EVIDENCE_ROOT/check.json"

# 5. D0 alone: anchor every family to this accepted closing and review fixed tasks.
# These are process-local reader settings, never a serving configuration change.
if [ "$INDEX" = 0 ]; then
  VF_MTA_LOCAL_PERMISSIONS=1 VF_MTA_PUBLISHED_RUN="$RUN" VF_MTA_PUBLISHED_DIGEST="$OUTPUT" \
  VF_BTR_REPORTING_GENERATION="$(field "$EVIDENCE_ROOT/check.json" VF_BTR_REPORTING_GENERATION)" \
  VF_MTA_OPERATIONAL_RECEIPT="$(field "$EVIDENCE_ROOT/accept.json" receipt)" \
  python -m tools.mdm_approval_day_workflow --run "$RUN" \
    --evidence "$EVIDENCE_ROOT/workflow.jsonl" > "$EVIDENCE_ROOT/workflow-result.json"
fi
echo 'STOP: run accepted without serving selection; verify the frozen family matrix before the next date.'
