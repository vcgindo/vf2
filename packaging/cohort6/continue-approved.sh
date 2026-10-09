#!/usr/bin/env bash
# Exact frozen June 6-7 handoff. Execution requires separate Approval B.
set -euo pipefail
python - <<'PY'
import hashlib,os,pathlib
expected=os.environ.get('COHORT6_APPROVAL_B_REQUEST_SHA256','')
actual=hashlib.sha256(pathlib.Path('/request-freeze/COHORT6_FROZEN_EXECUTION_REQUEST.json').read_bytes()).hexdigest()
if len(expected)!=64 or expected!=actual: raise SystemExit('Approval B request SHA256 is absent or differs; no execution')
PY

# Handoff command block 1
set -euo pipefail
export EVIDENCE_ROOT='/execution/two-date-007'
test ! -e "$EVIDENCE_ROOT"
mkdir "$EVIDENCE_ROOT"
exec 2> >(tee -a "$EVIDENCE_ROOT/stderr.log" >&2)
trap 'echo "STOP: command failed at line $LINENO; retain all receipts; do not retry" >&2' ERR
mkdir "$EVIDENCE_ROOT/pick"
mkdir "$EVIDENCE_ROOT/operations-day1" "$EVIDENCE_ROOT/operations-day2"
export ARTIFACT='/request/input.json'
export ARTIFACT_SHA='7ee7d940da3bab89ffeeddff94b4f2a7d9abace4aacdd589d698df6de85c24fc'
export FINALIZATION='/request/finalization.json'
export FINALIZATION_SHA='9a646e0eb3b455e495be3a6abb3cc11854594962def6171571bac5e834fef1b1'
export PICK_CONFIG='/request/pick.json'
export PICK_CONFIG_SHA='a775176974652ae0c228ab70a11ef4a5cbc2447b6535929397e914cc0e4b1c51'
export PICK_ROOT='/execution/two-date-007/pick'
export SHIPMENT='/request/shipment.json'
export SHIPMENT_SHA='dee26721ff67a7e09cb70dde849a43976a0132ea71a3a3402705a55b393664ae'
export PERMISSIONS='/request/permissions.json'
export PERMISSIONS_SHA='18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356'
export HIERARCHY_TEMPLATE='/request/hierarchy-template.json'
export HIERARCHY_TEMPLATE_SHA='d69c63804798b3cf31f98849341d7a61d38a37fe73c05e627aef1237e5ecfc6a'
export OPERATION_CONFIG='/request/operations-template.json'
export OPERATION_CONFIG_SHA='262d98a6b9f046552bbbe03afe67e10e56af7b13688540c922784e9effb3e2bd'
export OPERATION_OPENING='/request/operational-opening.json'
export OPERATION_OPENING_SHA='7ee4047b75a253e988b717ff7726d2aa72df3aa818b1fdb03295a4a08a5c9325'
export MDM_INSTALL_RECEIPT='/request/mdm-source.json'
export MDM_INSTALL_RECEIPT_SHA='3b2b08416bf62e0cdd02b8c179985d25bd355bdfe91f0202dadab487f49a4393'
export MDM_SOURCE='1'
export MDM_DIGEST='9b099c1f5b9853f2e2760d91ad549dcba883d375438135d58dab1efb63169cab'
export EMAIL_ENV='C6_BROAD_EMAIL'
export PASSWORD_ENV='C6_BROAD_PASSWORD'
export DJANGO_SETTINGS_MODULE=tools.cohort6_settings
export VF_MTA_DAILY_PUBLICATION=1 VF_MTA_SYNTHETIC_ROSTER=core-without-bor-v1
export VF_MTA_OPERATIONAL_POLICY=supported-synthetic-operational-v1 VF_MTA_ACTIONS_ENABLED=0
export VF_MTA_PUBLISHED_RUN='' VF_MTA_PUBLISHED_DIGEST='' VF_MTA_OPERATIONAL_RECEIPT=''
export VF_MTA_CONSUMPTION_POLICY='' VF_MTA_FIXTURE_FILE='' VF_MTA_FIXTURE_SHA256=''
export VF_MTA_TERMINAL_FILE='' VF_MTA_TERMINAL_SHA256='' VF_MTA_EXCESS_HISTORY_FILE='' VF_MTA_EXCESS_HISTORY_SHA256=''
export VF_MTA_PLANNING_EXTENSION='' VF_MTA_RRR_COLOUR_EXTENSION='' VF_MTA_GUIDED_EXCESS_DISPOSITION=''
export VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY=0 VF_MTA_PREACCEPTANCE_FILE='' VF_MTA_PREACCEPTANCE_SHA256=''
export VF_BPR_PREPARED=1 VF_GUIDED_PREPARED=1 VF_RRR_PREPARED=1 VF_HISTORY_REPORTS_PREPARED=1 VF_RESEARCH_AVAILABILITY_PREPARED=1
export VF_MTA_ACTION_TIME_ZONE=Asia/Kolkata
export VF_EVIDENCE_ROOT="$EVIDENCE_ROOT"

check_day() {
python - "$EVIDENCE_ROOT" "$1" "$2" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]);prefix=sys.argv[2]
run=json.loads((root/sys.argv[3]).read_text())
prepared=json.loads((root/(prefix+'-prepare.json')).read_text())
accepted=json.loads((root/(prefix+'-accept.json')).read_text())
checked=json.loads((root/(prefix+'-check.json')).read_text())
assert prepared['status']=='READY' and prepared['run_id']==run['run_id']
assert accepted['run_id']==run['run_id'] and accepted['activation'] and not accepted['selected']
assert checked['VF_MTA_PUBLISHED_RUN']==run['run_id'] and checked['VF_MTA_PUBLISHED_DIGEST']==run['output_digest']
assert checked['VF_MTA_OPERATIONAL_RECEIPT']==accepted['receipt']
PY
}

# Prepare native typed rows before binding read-time access. RRR is a prerequisite.
prepare_native() {
VF_MTA_PERMISSIONS_FILE='' VF_MTA_PERMISSIONS_SHA256='' \
VF_MTA_HIERARCHY_FILE='' VF_MTA_HIERARCHY_SHA256='' \
python - "$1" "$2" <<'PY'
import django,json,sys
django.setup()
from django.db import connection,transaction
from mta.runtime.models import CalculationRun,DailyUiPublication
from mta.presentation.daily_publication import configuration_identity,source_identity,recipe_identity,prepare
from mta.presentation.daily_preparation import prepare_layer,verify_layer
run=CalculationRun.objects.get(pk=sys.argv[1])
assert run.status=='SUCCEEDED' and run.output_digest==sys.argv[2]
lock=int.from_bytes(run.pk.bytes[:8],'big',signed=True)
with connection.cursor() as c:
 c.execute('SELECT pg_try_advisory_lock(%s)',[lock])
 if not c.fetchone()[0]:raise ValueError('Publication is busy')
try:
 identities=dict(output_digest=run.output_digest,source_digest=source_identity(run),configuration_digest=configuration_identity(),recipe_digest=recipe_identity())
 publication,_=DailyUiPublication.objects.get_or_create(run=run,defaults=identities)
 assert all(getattr(publication,k)==v for k,v in identities.items())
 if publication.status=='INCOMPLETE':
  with transaction.atomic():
   with connection.cursor() as c:c.execute("SELECT set_config('fresh.daily_publication_build',%s,true)",[str(run.pk)])
   receipt=prepare_layer(run,'rrr');verify_layer(run,'rrr',receipt)
 publication=prepare(run.pk,expected_output_digest=run.output_digest)
 print(json.dumps(dict(run_id=str(run.pk),status=publication.status,seal_digest=publication.seal_digest,layers=publication.layers),sort_keys=True))
 if publication.status!='READY':raise ValueError('Required report layers are incomplete')
finally:
 with connection.cursor() as c:c.execute('SELECT pg_advisory_unlock(%s)',[lock])
PY
}

# Handoff command block 2
python - "$ARTIFACT" "$ARTIFACT_SHA" "$FINALIZATION" "$FINALIZATION_SHA" \
  "$PICK_CONFIG" "$PICK_CONFIG_SHA" "$SHIPMENT" "$SHIPMENT_SHA" \
  "$PERMISSIONS" "$PERMISSIONS_SHA" "$HIERARCHY_TEMPLATE" "$HIERARCHY_TEMPLATE_SHA" <<'PY'
import hashlib, pathlib, sys
items = list(zip(sys.argv[1::2], sys.argv[2::2]))
for name, expected in items:
    path = pathlib.Path(name)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit('fixed file hash mismatch: ' + name)
print('fixed-file-hashes-pass')
PY

# Handoff command block 3
python -c 'import hashlib,sys; assert hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()==sys.argv[2]' \
  "$OPERATION_CONFIG" "$OPERATION_CONFIG_SHA"
python -c 'import hashlib,sys; assert hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()==sys.argv[2]' \
  "$OPERATION_OPENING" "$OPERATION_OPENING_SHA"
python -c 'import hashlib,sys; assert hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest()==sys.argv[2]' \
  "$MDM_INSTALL_RECEIPT" "$MDM_INSTALL_RECEIPT_SHA"

# Handoff command block 4
python - "$MDM_INSTALL_RECEIPT" "$MDM_SOURCE" "$MDM_DIGEST" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding='utf-8'))
if str(value.get('id')) != sys.argv[2] or value.get('digest') != sys.argv[3]:
    raise SystemExit('frozen MDM source identity differs')
receipt = value.get('receipt')
if not isinstance(receipt, dict) or set(receipt.get('families', {})) != {'1', '2', '3'}:
    raise SystemExit('complete installed MDM family receipt required')
print('installed-mdm-receipt-pass')
PY

# Reuse accepted root calculation/action/configuration receipts; never replay them.
python - "$EVIDENCE_ROOT" <<'PY'
import pathlib,hashlib,sys
hashes={'02-day1-run.json': 'a1ac5b240d1017decbd36558a3a8b1079f96521e48b628f175d62e5d1ad60362', '03-day1-hierarchy.json': '8e2c17b323637227fa5aabaf000d1c10a9e356e240959cb1a7d92e5594375e7f', '03-day1-hierarchy-receipt.json': '573825bf928ce24248ac2db18f750a7d967c7c3fc20e88dbae26f0fc7d75898c', '04-day1-actions-build.json': 'f75b2170adb65334ac0200593d5d37ba3e878b219867a921bd4bd0515537fa3f', '04-day1-actions-manifest.json': '29452ca32174f8c56ae208c1d20f09b8b988b9697067e37d80e92e7874110608', '05-day1-actions-execute.json': 'b5ff0884c7450c3a95950cc7c2e54b005c63cdc44be725a0f9b0aa571ee33a9e', '06-operation-configuration.json': '8a301cb7b0a624de6ae795de6813e452539d9218ed2668f8e14969c2753fe3ef', '06-day1-operation-request.json': '534ac3a1b77373b38f0e620716f38ed9ea9f598d574376195d40cb7a9f83bf18', '06-day1-operation.json': '20f290167075e6e5a2c99bc580b2acf7e0d5bbea15f4b333d0eb14b06ce23dbb', '06-day1-operation-check.json': '20f290167075e6e5a2c99bc580b2acf7e0d5bbea15f4b333d0eb14b06ce23dbb', '06-native-transition.json': '626e1b0bb8ec2b33dd8f51a3259269aafdaec81cf00e89b01d073425431d0895', '06-original-publication.json': '7414b88f8638109b456ab8e264a0893659b07e3880e0d2d35a32ade781416bac', '07-day1-prepare.json': '29561d72cb91919690dff70185adb5c124cce5855069a2f3987922b892416273'}
for name,expected in hashes.items():
 raw=(pathlib.Path('/prior')/name).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==expected
 with (pathlib.Path(sys.argv[1])/name).open('xb') as f:f.write(raw)
PY
export DAY1_RUN='71a5addc-dcb7-49ca-811d-6cd93886d4e5'
export DAY1_OUTPUT='7075127ea7fc6fa3d3d05f00bcb6e771eb1bf6401a811cbf2c97158e5976235b'
export DAY1_HIERARCHY="$EVIDENCE_ROOT/03-day1-hierarchy.json"
DAY1_HIERARCHY_SHA="$(python -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$DAY1_HIERARCHY")"
export DAY1_HIERARCHY_SHA
OPERATION_CONFIGURATION="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["configuration_id"])' "$EVIDENCE_ROOT/06-operation-configuration.json")"
export OPERATION_CONFIGURATION

# Reuse the verified successful operation and preserve its failed predecessor.
DAY1_ATTEMPT="$(python -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["status"]=="SUCCEEDED"; print(d["attempt"])' "$EVIDENCE_ROOT/06-day1-operation.json")"
export DAY1_ATTEMPT
# Handoff command block 12

   VF_MTA_DAILY_PUBLICATION=1 VF_MTA_SYNTHETIC_ROSTER=core-without-bor-v1 \
   VF_MTA_ACTIONS_ENABLED=0 VF_MTA_OPERATIONAL_POLICY='supported-synthetic-operational-v1' \
   VF_MTA_PERMISSIONS_FILE="$PERMISSIONS" VF_MTA_PERMISSIONS_SHA256="$PERMISSIONS_SHA" \
   VF_MTA_HIERARCHY_FILE="$DAY1_HIERARCHY" VF_MTA_HIERARCHY_SHA256="$DAY1_HIERARCHY_SHA" \
   python -m django accept_daily_operational --run-id "$DAY1_RUN" \
     --output-digest "$DAY1_OUTPUT" --attempt "$DAY1_ATTEMPT" \
     --artifact "$ARTIFACT" --finalization-config "$FINALIZATION" \
     --pick-config "$PICK_CONFIG" --shipment-input "$SHIPMENT" \
     > "$EVIDENCE_ROOT/07-day1-accept.json"
   DAY1_ACCEPTANCE_RECEIPT="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["receipt"])' "$EVIDENCE_ROOT/07-day1-accept.json")"
   export DAY1_ACCEPTANCE_RECEIPT
   VF_MTA_DAILY_PUBLICATION=1 VF_MTA_SYNTHETIC_ROSTER=core-without-bor-v1 \
   VF_MTA_ACTIONS_ENABLED=0 VF_MTA_OPERATIONAL_POLICY='supported-synthetic-operational-v1' \
   VF_MTA_PERMISSIONS_FILE="$PERMISSIONS" VF_MTA_PERMISSIONS_SHA256="$PERMISSIONS_SHA" \
   VF_MTA_HIERARCHY_FILE="$DAY1_HIERARCHY" VF_MTA_HIERARCHY_SHA256="$DAY1_HIERARCHY_SHA" \
   python -m django check_daily_selection --run-id "$DAY1_RUN" --output-digest "$DAY1_OUTPUT" \
     > "$EVIDENCE_ROOT/07-day1-check.json"

check_day 07-day1 02-day1-run.json

# Handoff command block 13
python -m django run_daily "$ARTIFACT" --sha256 "$ARTIFACT_SHA" \
     --day-index 1 --revision 'cohort6-approved-successor-001' --predecessor "$DAY1_RUN" \
     --mdm-source "$MDM_SOURCE" --mdm-source-digest "$MDM_DIGEST" \
     --bpr-remark-horizon '90' \
     --finalization-config "$FINALIZATION" --finalization-config-sha256 "$FINALIZATION_SHA" \
     --complete-pick-policy 'canonical-tied-order-v1' --pick-output-root "$PICK_ROOT" \
     --pick-config "$PICK_CONFIG" --pick-config-sha256 "$PICK_CONFIG_SHA" \
     --shipment-input "$SHIPMENT" --shipment-sha256 "$SHIPMENT_SHA" \
     --operational-sources 'cohort2-operational-sources-v1' \
     --operational-input-sources 'cohort2-input-tables-v1' \
     --operational-force-sources 'cohort2-pre-clear-force-v1' \
     > "$EVIDENCE_ROOT/08-day2-run.json"
   DAY2_RUN="$(python -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["status"]=="SUCCEEDED" and d["business_date"]=="2026-06-07"; print(d["run_id"])' "$EVIDENCE_ROOT/08-day2-run.json")"
   export DAY2_RUN
   DAY2_OUTPUT="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["output_digest"])' "$EVIDENCE_ROOT/08-day2-run.json")"
   export DAY2_OUTPUT

# Handoff command block 14
python -m tools.cohort6_bind_day --template "$HIERARCHY_TEMPLATE" \
     --template-sha256 "$HIERARCHY_TEMPLATE_SHA" \
     --run-receipt "$EVIDENCE_ROOT/08-day2-run.json" --business-date 2026-06-07 \
     --output "$EVIDENCE_ROOT/09-day2-hierarchy.json" \
     > "$EVIDENCE_ROOT/09-day2-hierarchy-receipt.json"
   DAY2_HIERARCHY="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["path"])' "$EVIDENCE_ROOT/09-day2-hierarchy-receipt.json")"
   export DAY2_HIERARCHY
   DAY2_HIERARCHY_SHA="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha256"])' "$EVIDENCE_ROOT/09-day2-hierarchy-receipt.json")"
   export DAY2_HIERARCHY_SHA

   VF_MTA_PERMISSIONS_FILE="$PERMISSIONS" VF_MTA_PERMISSIONS_SHA256="$PERMISSIONS_SHA" \
   VF_MTA_HIERARCHY_FILE="$DAY2_HIERARCHY" VF_MTA_HIERARCHY_SHA256="$DAY2_HIERARCHY_SHA" \
   DJANGO_SETTINGS_MODULE=tools.cohort6_settings \
   python -m tools.cohort6_actions --run "$DAY2_RUN" \
     --email-environment "$EMAIL_ENV" --password-environment "$PASSWORD_ENV" \
     build-manifest --output "$EVIDENCE_ROOT/09-day2-actions-manifest.json" \
     --artifact "$ARTIFACT" --artifact-sha256 "$ARTIFACT_SHA" \
     --finalization "$FINALIZATION" --finalization-sha256 "$FINALIZATION_SHA" \
     --pick-config "$PICK_CONFIG" --pick-config-sha256 "$PICK_CONFIG_SHA" \
     --shipment "$SHIPMENT" --shipment-sha256 "$SHIPMENT_SHA" \
     > "$EVIDENCE_ROOT/09-day2-actions-build.json"
   export DAY2_MANIFEST="$EVIDENCE_ROOT/09-day2-actions-manifest.json"
   DAY2_MANIFEST_SHA="$(python -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$DAY2_MANIFEST")"
   export DAY2_MANIFEST_SHA

   VF_MTA_PERMISSIONS_FILE="$PERMISSIONS" VF_MTA_PERMISSIONS_SHA256="$PERMISSIONS_SHA" \
   VF_MTA_HIERARCHY_FILE="$DAY2_HIERARCHY" VF_MTA_HIERARCHY_SHA256="$DAY2_HIERARCHY_SHA" \
   VF_MTA_PREACCEPTANCE_FILE="$DAY2_MANIFEST" VF_MTA_PREACCEPTANCE_SHA256="$DAY2_MANIFEST_SHA" \
   DJANGO_SETTINGS_MODULE=tools.cohort6_settings \
   python -m tools.cohort6_actions --run "$DAY2_RUN" \
     --email-environment "$EMAIL_ENV" --password-environment "$PASSWORD_ENV" execute \
     > "$EVIDENCE_ROOT/09-day2-actions-execute.json"

# Handoff command block 15
python - "$EVIDENCE_ROOT/10-day2-operation-request.json" "$DAY2_RUN" "$DAY2_OUTPUT" "$DAY1_ATTEMPT" "$OPERATION_CONFIGURATION" <<'PY'
import json, pathlib, sys
target, run_id, output, predecessor, configuration = sys.argv[1:]
value = {'run_id': run_id,
         'configuration_id': configuration,
         'request_key': 'cohort6-cont005-day2-2026-06-07',
         'owned_root': '/execution/two-date-007/operations-day2',
         'expected_output_digest': output,
         'predecessor_id': predecessor}
with pathlib.Path(target).open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2); stream.write('\n')
PY
    python -m django cohort2_operational materialize \
      --request "$EVIDENCE_ROOT/10-day2-operation-request.json" \
      > "$EVIDENCE_ROOT/10-day2-operation.json"
    DAY2_ATTEMPT="$(python -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["status"]=="SUCCEEDED"; print(d["attempt"])' "$EVIDENCE_ROOT/10-day2-operation.json")"
    export DAY2_ATTEMPT
    python -m django cohort2_operational check --attempt "$DAY2_ATTEMPT" \
      > "$EVIDENCE_ROOT/10-day2-operation-check.json"

# Handoff command block 16
export VF_MTA_PREDECESSOR_HIERARCHY_FILE="$DAY1_HIERARCHY"
prepare_native "$DAY2_RUN" "$DAY2_OUTPUT" \
      > "$EVIDENCE_ROOT/11-day2-prepare.json"
    VF_MTA_DAILY_PUBLICATION=1 VF_MTA_SYNTHETIC_ROSTER=core-without-bor-v1 \
    VF_MTA_ACTIONS_ENABLED=0 VF_MTA_OPERATIONAL_POLICY='supported-synthetic-operational-v1' \
    VF_MTA_PERMISSIONS_FILE="$PERMISSIONS" VF_MTA_PERMISSIONS_SHA256="$PERMISSIONS_SHA" \
    VF_MTA_HIERARCHY_FILE="$DAY2_HIERARCHY" VF_MTA_HIERARCHY_SHA256="$DAY2_HIERARCHY_SHA" \
    python -m django accept_daily_operational --run-id "$DAY2_RUN" \
      --output-digest "$DAY2_OUTPUT" --attempt "$DAY2_ATTEMPT" \
      --artifact "$ARTIFACT" --finalization-config "$FINALIZATION" \
      --pick-config "$PICK_CONFIG" --shipment-input "$SHIPMENT" \
      > "$EVIDENCE_ROOT/11-day2-accept.json"
    DAY2_ACCEPTANCE_RECEIPT="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["receipt"])' "$EVIDENCE_ROOT/11-day2-accept.json")"
    export DAY2_ACCEPTANCE_RECEIPT
    VF_MTA_DAILY_PUBLICATION=1 VF_MTA_SYNTHETIC_ROSTER=core-without-bor-v1 \
    VF_MTA_ACTIONS_ENABLED=0 VF_MTA_OPERATIONAL_POLICY='supported-synthetic-operational-v1' \
    VF_MTA_PERMISSIONS_FILE="$PERMISSIONS" VF_MTA_PERMISSIONS_SHA256="$PERMISSIONS_SHA" \
    VF_MTA_HIERARCHY_FILE="$DAY2_HIERARCHY" VF_MTA_HIERARCHY_SHA256="$DAY2_HIERARCHY_SHA" \
    python -m django check_daily_selection --run-id "$DAY2_RUN" --output-digest "$DAY2_OUTPUT" \
      > "$EVIDENCE_ROOT/11-day2-check.json"

check_day 11-day2 08-day2-run.json

python - "$EVIDENCE_ROOT" <<'PY'
import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[1])
for prefix,runfile in [('07-day1','02-day1-run.json'),('11-day2','08-day2-run.json')]:
 run=json.loads((root/runfile).read_text())
 prepared=json.loads((root/(prefix+'-prepare.json')).read_text())
 accepted=json.loads((root/(prefix+'-accept.json')).read_text())
 checked=json.loads((root/(prefix+'-check.json')).read_text())
 assert prepared['status']=='READY' and prepared['run_id']==run['run_id']
 assert accepted['run_id']==run['run_id'] and accepted['activation'] and not accepted['selected']
 assert checked['VF_MTA_PUBLISHED_RUN']==run['run_id'] and checked['VF_MTA_PUBLISHED_DIGEST']==run['output_digest']
 assert checked['VF_MTA_OPERATIONAL_RECEIPT']==accepted['receipt']
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.json'))}
with (root/'terminal-receipts.json').open('x') as f: json.dump({'status':'TWO_DATE_UNSELECTED_CHECKS_PASS','files':files},f,indent=2)
print('STOP: two dates checked; no serving configuration applied')
PY
