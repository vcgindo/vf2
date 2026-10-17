"""Exact registered synthetic package admission; no calculation or selection."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def registry():
    value = json.loads((ROOT/'baseline/offline-temporal-scenarios-v1.json').read_text())
    spec = (ROOT/'baseline/synthetic-temporal-business-v1.json').read_bytes()
    if hashlib.sha256(spec).hexdigest() != value['scenario_sha256']:
        raise ValueError('Approved scenario specification changed')
    return value


def admit(raw, expected):
    value = registry()
    entries = [row for row in value['scenarios'].values() if row['sha256']==expected]
    if len(entries)!=1 or hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('Unregistered or altered offline input')
    artifact = json.loads(raw)
    if (artifact.get('schema')!='fresh-synthetic-temporal-v1'
            or artifact.get('scenario_sha256')!=value['scenario_sha256']
            or artifact.get('catalogue_sha256')!=value['catalogue_sha256']
            or len(artifact['case']['static_day']['raw_master'])!=entries[0]['pairs']
            or len(artifact['case']['days'])!=21
            or artifact['case']['profile'].get('daily_publication') is not True):
        raise ValueError('Registered scenario contract differs')
    return artifact
def require_run(run):
    """Admit only independently accepted runs of the frozen offline scenario."""
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    pins = registry()
    capture = MdmDailyInputCapture.objects.select_related('source').get(run=run)
    receipt = capture.source.receipt
    if (run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED'
            or run.parity_summary.get('status') not in ('PASS', 'PASS_WITH_LEGACY_FLAWS')
            or not receipt.get('offline_owner')
            or receipt.get('scenario_sha256') != pins['scenario_sha256']
            or receipt.get('artifact_sha256') not in {r['sha256'] for r in pins['scenarios'].values()}):
        raise ValueError('Accepted frozen offline scenario run required')
    from mta.presentation.offline_rrr import require_proof
    require_proof(run)
    return receipt
