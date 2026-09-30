"""Validate registered temporal external facts without generating replacements.

The ledger is external operational data, never a source of computed DBM state.
Opening historical facts and every future daily fact must reconcile to the same
dated shipments. This validation does not certify engine or action parity.
"""
from collections import defaultdict
from datetime import date, timedelta
import argparse
import hashlib
import json
from pathlib import Path

from mta.serialization import digest

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(row):
    return row['SKUCode'], row.get('WhCode', row.get('WHCode'))


def integer(value):
    require(type(value) is int and value >= 0, 'Expected a nonnegative integer fact')
    return value


def validate(payload):
    case = payload['case']
    ledger = case['external_fact_ledger']
    shipments = ledger['shipments']
    checks = ledger['daily_reconciliation']
    require(ledger['git_duration_formula'] == 'max(1, (RLT + 1) // 2)', 'Undeclared transit rounding')
    require(digest(shipments) == ledger['shipments_sha256'], 'Shipment digest differs')
    require(digest(checks) == ledger['reconciliation_sha256'], 'Reconciliation digest differs')
    masters = case['static_day']['raw_master']
    rlt = {identity(row): integer(row['RLT']) for row in masters}
    require(len(rlt) == len(masters) and all(rlt.values()), 'Missing/duplicate identity or nonpositive RLT')
    dates = [date.fromisoformat(day['business_date']) for day in case['days']]
    opening_date = date.fromisoformat(case['opening_date'])
    require(len(dates) == 3 * max(rlt.values()), 'Run must span 3 times maximum selected RLT')
    require(dates == [opening_date + timedelta(days=i+1) for i in range(len(dates))], 'Nonconsecutive horizon')

    grouped = defaultdict(list)
    dispatched = defaultdict(int)
    received = defaultdict(int)
    ids = set()
    for shipment in shipments:
        key = identity(shipment)
        require(key in rlt and shipment['shipment_id'] not in ids, 'Unknown/duplicate shipment identity')
        ids.add(shipment['shipment_id'])
        quantity = integer(shipment['quantity'])
        require(quantity > 0, 'Shipment quantity must be positive')
        start = date.fromisoformat(shipment['dispatch_date'])
        end = date.fromisoformat(shipment['receipt_date'])
        duration = max(1, (rlt[key] + 1) // 2)  # positive integer half-up rounding
        require((end-start).days == duration == shipment['git_duration_days'], 'Shipment duration is not rounded half-RLT')
        grouped[key].append((start, end, quantity))
        dispatched[key, start] += quantity
        received[key, end] += quantity

    by_identity = defaultdict(list)
    by_key = {}
    for row in checks:
        key = identity(row)
        day = date.fromisoformat(row['ReportDate'])
        require(key in rlt and (key, day) not in by_key, 'Unknown/duplicate ledger fact')
        for field in ('opening_stock', 'receipts', 'consumption', 'closing_stock',
                      'opening_git', 'dispatches', 'git_receipts', 'closing_git'):
            integer(row[field])
        by_key[key, day] = row
        by_identity[key].append((day, row))
    require(set(by_identity) == set(rlt), 'Ledger population differs from master population')
    for key, timeline in by_identity.items():
        timeline.sort(key=lambda item: item[0])
        first = timeline[0][0]
        stock = timeline[0][1]['opening_stock']
        git = sum(q for dispatch, receipt, q in grouped[key] if dispatch < first <= receipt)
        require(first <= opening_date and timeline[-1][0] == dates[-1], 'Ledger does not cover opening and complete horizon')
        for index, (day, row) in enumerate(timeline):
            require(day == first + timedelta(days=index), 'Ledger skips a day')
            require(row['opening_stock'] == stock and row['opening_git'] == git, 'Ledger predecessor differs')
            require(row['receipts'] == row['git_receipts'] == received[key, day], 'Receipts do not equal dated shipments')
            require(row['dispatches'] == dispatched[key, day], 'Dispatches do not equal dated shipments')
            stock += row['receipts'] - row['consumption']
            git += row['dispatches'] - row['git_receipts']
            require(stock == row['closing_stock'] and git == row['closing_git'], 'Stock/GIT balance does not reconcile')
        require(sum(q for _, _, q in grouped[key]) == sum(row['receipts'] for _, row in timeline), 'Shipments outside the declared receipt ledger')

    def validate_facts(rows, expected_keys, label):
        seen = set()
        for row in rows:
            key = identity(row), date.fromisoformat(row['ReportDate'][:10])
            require(key not in seen and key in by_key, 'Unknown/duplicate '+label+' fact')
            seen.add(key)
            expected = by_key[key]
            for actual, field in (('Stock','closing_stock'), ('GIT','closing_git'),
                                  ('Receipts','receipts'), ('Consumption','consumption')):
                require(integer(row[actual]) == expected[field], label+' differs from ledger: '+actual)
        require(seen == expected_keys, label+' population differs')
        return len(seen)

    historical = {key for key in by_key if key[1] <= opening_date}
    validate_facts(case['opening']['bpr']['DailyConsumption'], historical, 'opening BPR')
    validate_facts(case['opening']['dbm']['DailyConsumption'], historical, 'opening DBM')
    for day, entry in zip(dates, case['days']):
        validate_facts(entry['raw_daily'], {(key, day) for key in rlt}, 'daily input')
    counts = dict(identities=len(rlt), fact_rows=len(checks), shipments=len(shipments))
    require(counts == ledger['counts'], 'Declared counts differ')
    return dict(status='PASS', counts=counts, computed_days=len(dates), max_rlt=max(rlt.values()),
                first_day=dates[0].isoformat(), last_day=dates[-1].isoformat(),
                git_duration_formula=ledger['git_duration_formula'],
                shipments_sha256=ledger['shipments_sha256'], reconciliation_sha256=ledger['reconciliation_sha256'],
                scope='External facts only; not engine/action or full raw-ingestion acceptance')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    raw = args.artifact.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    registered = json.loads((ROOT/'baseline/manifest.json').read_text())['retained_resources']
    require(sha in {r['sha256'] for r in registered}, 'Unregistered artifact')
    receipt = dict(artifact=str(args.artifact), artifact_sha256=sha,
                   validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), **validate(json.loads(raw)))
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with args.destination.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
