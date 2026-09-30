"""Reuse the exact approved raw-producer fixtures and their canonical receipts."""
import argparse
import json
from pathlib import Path
import time

from mta.planning.engine import calculate_current_day
from mta.serialization import storage
from parity.current_day import compare
from parity.verify_current_day import checksum, file_hash

ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOT = Path('F:/vflow_integrated/.local-stage7/block2-replay')
RECEIPTS = (
    'daily-order-connection/r1_daily_order_nonmaster-20260927T090229823937Z.json',
    'connected-inputs-controls/r1_connected_inputs_controls-20260927T074405076180Z.json',
    'control-diagnostics/r1_control_diagnostics-20260927T093048441588Z.json',
    'transit-tags/r1_transit_tags-20260927T092046680110Z.json',
)


def options(payload):
    schema = payload['schema']
    master = payload.get('master_state', {})
    order = payload.get('order_input', {})
    opening = order.get('opening_orders', [])
    return dict(
        master_state_required=schema in {f'r1-current-day-input-v{n}' for n in (5,6,7,8)},
        importer_validation_required=schema in {f'r1-current-day-input-v{n}' for n in (6,7,8)},
        supplier_required=schema in {f'r1-current-day-input-v{n}' for n in (7,8)},
        daily_required=schema == 'r1-current-day-input-v8',
        phase_required='phase_control_input' in master,
        accepted_required='accepted_norm_input' in master,
        order_input_required='order_input' in payload,
        order_parts_required=bool(order) and ('identity_last_value' in order
            or len({r['CustomerOrderId'] for r in opening}) < len(opening)),
        season_required='season_control_input' in master,
        tags_required='transit_tag_input' in master,
        diagnostics_required=bool(master.get('control_diagnostics')),
    )


def verify(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    results = []
    for name in RECEIPTS:
        path = LEGACY_ROOT / name
        retained = json.loads(path.read_text(encoding='utf-8'))
        fixture = ROOT / 'mta/fixtures' / retained['fixture']
        payload = json.loads(fixture.read_text(encoding='utf-8'))
        if payload != retained['input'] or checksum(payload) != retained['input_sha256']:
            raise ValueError('Retained input identity differs: ' + name)
        if retained['result']['parity'] != 'PASS':
            raise ValueError('Receipt is not accepted canonical comparison: ' + name)
        for script in retained['legacy']['scripts']:
            if file_hash(Path(script['path'])) != script['sha256']:
                raise ValueError('Canonical script differs: ' + script['path'])
        started = time.monotonic()
        modern = storage(calculate_current_day(payload))
        if 'pick_remaining' not in retained['legacy']['checkpoints']:
            # This older receipt predates the required remaining-Pick contract.
            # Do not seed an empty answer, drop the assertion or declare parity.
            gap = dict(fixture=retained['fixture'], status='RECEIPT_INCOMPLETE',
                       missing=['pick_remaining'], comparisons=0,
                       receipt_sha256=file_hash(path), modern=modern)
            (destination / retained['fixture']).write_text(json.dumps(gap, indent=2), encoding='utf-8')
            results.append({k:v for k,v in gap.items() if k != 'modern'})
            print(json.dumps(results[-1]), flush=True)
            continue
        contracts = compare(retained['legacy']['checkpoints'], modern, **options(payload))
        expected_roster = set(retained['result']['checkpoints'])
        passed = expected_roster == set(contracts) and all(v['status'] == 'PASS' for v in contracts.values())
        evidence = dict(fixture=retained['fixture'], input_sha256=checksum(payload),
                        legacy_receipt=str(path), legacy_receipt_sha256=file_hash(path),
                        legacy_execution='RETAINED_CANONICAL_RECEIPT', status='PASS' if passed else 'FAIL',
                        contracts=contracts, modern=modern,
                        seconds=round(time.monotonic()-started, 3))
        (destination / retained['fixture']).write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding='utf-8')
        summary = {k: evidence[k] for k in ('fixture','status','seconds')}
        summary.update(comparisons=len(contracts), failures=[k for k,v in contracts.items() if v['status'] != 'PASS'])
        results.append(summary)
        print(json.dumps(summary), flush=True)
    (destination / 'summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    return all(r['status'] == 'PASS' for r in results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination')
    raise SystemExit(0 if verify(parser.parse_args().destination) else 1)
