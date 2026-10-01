"""Prove approved terminal-only empty transit from retained external facts.

No artifact generation, calculation replay, database write or source edit.
"""
import json
from pathlib import Path
import sys
import ijson
from parity.output_archive import file_sha
from mta.serialization import digest

ARTIFACT = Path('F:/vflow_integrated/.local-stage7/block3-sizeable/v1/sizeable-input.json')
ARTIFACT_SHA = '0f3084b7a6fb60b84edbd7c4dc01fef3c4b40f1a7c389ec82f88b9ad22519546'
LEDGER = Path('D:/freshvcf-build/evidence/f2-ledger-sizeable-001.json')
PRODUCER = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/Importer/ValidateGoodsInTransit.sql')
PRODUCER_SHA = '6db973f9f72e28fcb6d22d8e9ce2e069708b6f656a7169573680afbd45e81257'
DATE = '2026-06-17'


def items(prefix):
    with ARTIFACT.open('rb') as stream:
        yield from ijson.items(stream, prefix, use_float=True)


def audit():
    assert file_sha(ARTIFACT) == ARTIFACT_SHA
    previous = json.loads(LEDGER.read_text())
    assert previous['status'] == 'PASS' and previous['artifact_sha256'] == ARTIFACT_SHA
    assert previous['last_day'] == DATE and previous['counts']['identities'] == 1240
    assert file_sha(PRODUCER) == PRODUCER_SHA
    shipments = list(items('case.external_fact_ledger.shipments.item'))
    assert digest(shipments) == previous['shipments_sha256']
    outstanding = [r for r in shipments if r['dispatch_date'] <= DATE < r['receipt_date']]
    terminal = [d for d in items('case.days.item') if d['business_date'] == DATE]
    assert len(terminal) == 1
    rows = terminal[0]['raw_daily']
    assert len(rows) == len({(r['SKUCode'], r['WhCode']) for r in rows}) == 1240
    assert not outstanding and all(type(r['GIT']) is int and r['GIT'] == 0 for r in rows)
    assert file_sha(ARTIFACT) == ARTIFACT_SHA
    return dict(status='PASS_TERMINAL_EMPTY_TRANSIT_BOUNDARY', business_date=DATE,
        artifact=str(ARTIFACT), artifact_sha256=ARTIFACT_SHA,
        retained_ledger_receipt=str(LEDGER), retained_ledger_receipt_sha256=file_sha(LEDGER),
        producer=str(PRODUCER), producer_sha256=PRODUCER_SHA,
        shipments=len(shipments), outstanding_shipments=0, terminal_pairs=len(rows), terminal_git_sum=0,
        last_dispatch=max(r['dispatch_date'] for r in shipments),
        last_receipt=max(r['receipt_date'] for r in shipments),
        shipments_sha256=previous['shipments_sha256'],
        ancillary={'InTransitData': [], 'BPRReport_RemarkDetails': []},
        authorization='call_zsFKJgePAcUNJ7FUdBlryYEB: Approve terminal-only supplement',
        remarks_basis='Explicitly approved initial empty remarks for new Fresh application, not engine-produced data',
        qualification='Terminal consumer inputs only; NOT nonempty logistics, producer replay or historical-date parity',
        f2_mutations=False, engine_replays=0)


if __name__ == '__main__':
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    result = audit()
    with target.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
