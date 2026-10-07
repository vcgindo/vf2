"""Generate the approved physical scenario; never call either calculation engine."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mta.serialization import digest
from parity.temporal_ledger import validate as validate_ledger
from tools.reduce_daily_smoke import _reduce_case


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def rounded(value):
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def pair(row):
    return row['SKUCode'], row.get('WhCode', row.get('WHCode'))


def physical_ledger(masters, spec):
    keys = [pair(row) for row in masters]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate catalogue occurrence')
    master = dict(zip(keys, masters)); children = defaultdict(list)
    for key, row in master.items():
        children[key[0], row['ParentWhCode']].append(key)
        if type(row['PackSize']) is not int or row['PackSize'] < 1:
            raise ValueError('Undeclared pack size')
    hashes = {key:int.from_bytes(hashlib.sha256(
        (str(spec['seed'])+'|'+'|'.join(key)).encode()).digest()[:8], 'big') for key in keys}
    base = {key:max(1, rounded(Decimal(row['Norm'])/(3*row['RLT']))) for key,row in master.items()}
    standing = {}; visiting = set()
    def supply(key):
        if key in visiting:
            raise ValueError('Cyclic retained parent topology')
        if key not in standing:
            visiting.add(key)
            quantity = base[key]+sum(supply(child) for child in children[key])
            lot = master[key]['PackSize']
            standing[key] = ((quantity+lot-1)//lot)*lot
            visiting.remove(key)
        return standing[key]
    for key in keys:
        supply(key)
    first = date.fromisoformat(spec['first_day']); last = first+timedelta(days=spec['days']-1)
    stocks = {key:row['Norm'] for key,row in master.items()}
    git = dict.fromkeys(keys, 0)
    arrivals = defaultdict(lambda:defaultdict(int))
    shipments, checks, events, facts = [], [], [], {}
    for index in range(-spec['warmup_days'], spec['days']):
        today = first+timedelta(days=index); stamp = str(today)
        opening_stock, opening_git = dict(stocks), dict(git)
        requested, sales, outbound, inbound = {}, {}, defaultdict(int), defaultdict(int)
        for key in keys:
            stocks[key] += arrivals[today][key]; git[key] -= arrivals[today][key]
            factor = Decimal(spec['weekday_factors'][today.weekday()])
            if index >= 0:
                factor *= Decimal(spec['week_factors'][index//7])
            slot = hashes[key]%10
            if slot in (7,8):
                factor *= 3 if (index+hashes[key]%3)%3 == 0 else 0
            if slot == 9:
                promo = spec['promotion']
                factor *= (Decimal(promo['first_factor']) if index in promo['first_indices'] else
                           Decimal(promo['second_factor']) if index in promo['second_indices'] else 1)
            requested[key] = rounded(base[key]*factor)
            sales[key] = min(stocks[key], requested[key]); stocks[key] -= sales[key]
        shortages = {}
        for key in keys:
            row = master[key]; duration = max(1, (row['RLT']+1)//2)
            receipt_day = today+timedelta(days=duration)
            quantity = standing[key] if receipt_day <= last else 0
            parent = key[0], row['ParentWhCode']
            actual = min(quantity, (stocks[parent]//row['PackSize'])*row['PackSize']) if parent in master else quantity
            shortages[key] = quantity-actual
            if parent in master:
                stocks[parent] -= actual; outbound[parent] += actual
            if actual:
                identifier = 'R47-'+key[0]+'-'+key[1]+'-'+stamp
                shipments.append(dict(shipment_id=identifier, SKUCode=key[0], WhCode=key[1],
                    quantity=actual, dispatch_date=stamp, receipt_date=str(receipt_day), git_duration_days=duration))
                arrivals[receipt_day][key] += actual; git[key] += actual; inbound[key] += actual
        daily = []
        for key in keys:
            consumption = sales[key]+outbound[key]
            if min(stocks[key], git[key]) < 0:
                raise ValueError('Physical supply overdraw')
            daily.append(dict(SKUCode=key[0], WhCode=key[1], Stock=stocks[key], Consumption=consumption,
                Receipts=arrivals[today][key], GIT=git[key], PSO=0, ReportDate=stamp))
            checks.append(dict(SKUCode=key[0], WhCode=key[1], ReportDate=stamp,
                opening_stock=opening_stock[key], receipts=arrivals[today][key], consumption=consumption,
                closing_stock=stocks[key], opening_git=opening_git[key], dispatches=inbound[key],
                git_receipts=arrivals[today][key], closing_git=git[key]))
            events.append(dict(SKUCode=key[0], WhCode=key[1], ReportDate=stamp,
                requested=requested[key], realized=sales[key], lost=requested[key]-sales[key],
                parent_outbound=outbound[key], unsupplied=shortages[key]))
        facts[index] = daily
    ledger = dict(schema='block3-sizeable-external-ledger-v1', status='PASS',
        git_duration_formula='max(1, (RLT + 1) // 2)', shipments=shipments,
        daily_reconciliation=checks, shipments_sha256=digest(shipments), reconciliation_sha256=digest(checks),
        counts=dict(identities=len(keys), fact_rows=len(checks), shipments=len(shipments)))
    return ledger, facts, events


def build(parent_raw, catalogue_raw, spec_raw):
    spec = json.loads(spec_raw)
    if sha(parent_raw) != spec['parent_sha256'] or sha(catalogue_raw) != spec['catalogue_sha256']:
        raise ValueError('Pinned parent/catalogue bytes differ')
    catalogue = json.loads(catalogue_raw)['raw_master']
    parent = json.loads(parent_raw); case = deepcopy(parent['case'])
    original = case['static_day']['raw_master']
    if len(catalogue) != 1240 or Counter(row['RLT'] for row in catalogue) != {4:312,5:299,6:296,7:333}:
        raise ValueError('Approved RLT roster differs')
    if any({**old,'RLT':old['RLT']+3} != new for old,new in zip(original,catalogue)):
        raise ValueError('Catalogue changed outside the approved RLT amendment')
    rlts = {pair(row):row['RLT'] for row in catalogue}
    def amend(value):
        if isinstance(value, dict):
            key = (value.get('SKUCode',value.get('sku_code')), value.get('WhCode',value.get('WHCode',value.get('location_code'))))
            for field in ('RLT','rlt'):
                if field in value and key in rlts:
                    value[field] = rlts[key]
            for child in value.values(): amend(child)
        elif isinstance(value,list):
            for child in value: amend(child)
    amend(case)
    case['static_day']['raw_master'] = deepcopy(catalogue)
    ledger, facts, events = physical_ledger(catalogue,spec)
    case['external_fact_ledger'] = ledger
    history = [row for index,rows in facts.items() if index < 0 for row in rows]
    case['opening']['bpr']['DailyConsumption'] = [
        {**{('WHCode' if k=='WhCode' else k):v for k,v in row.items()},'BlueZone':0} for row in history]
    case['opening']['dbm']['DailyConsumption'] = [
        {**{k:v for k,v in row.items() if k!='PSO'},'BlueZone':0} for row in history]
    day_template = deepcopy(case['days'][0])
    for name in ('accepted_feed','new_force_requests','order_feed'): day_template[name] = []
    day_template['control_requests'] = {name:[] for name in day_template['control_requests']}
    first = date.fromisoformat(spec['first_day'])
    case['days'] = [{**deepcopy(day_template), 'business_date':str(first+timedelta(days=i)),
                     'raw_daily':facts[i]} for i in range(spec['days'])]
    case['commands'] = [command for command in case['commands'] if command['operation']=='SLEEP']
    case['opening_date'] = str(first-timedelta(days=1))
    case['case'] = spec['version']
    case['profile']['daily_publication'] = True
    case['profile']['synthetic_action_policy'] = spec['action_policy']
    case['profile']['daily_publication_config'] = {'bpr_remark_horizon':spec['bpr_remark_horizon']}
    payload = dict(schema='fresh-synthetic-temporal-v1', scenario_sha256=sha(spec_raw),
                   catalogue_sha256=sha(catalogue_raw), parent_sha256=sha(parent_raw), case=case)
    validate_scenario(payload, events, spec, catalogue)
    return payload, events


def validate_scenario(payload, events, spec, catalogue):
    """Independent cross-owner balances in addition to the retained validator."""
    case = payload['case']; masters = case['static_day']['raw_master']
    if masters != catalogue or len(masters) != 1240:
        raise ValueError('Scenario catalogue occurrences differ')
    if spec['days'] != 21 or spec['warmup_days'] != 21:
        raise ValueError('Shared approved horizon differs')
    proof = validate_ledger(payload)
    keys = {pair(row) for row in masters}; mapping = {pair(row):row for row in masters}
    first = date.fromisoformat(spec['first_day'])
    dates = [str(first+timedelta(days=i)) for i in range(21)]
    if [day['business_date'] for day in case['days']] != dates or sum(len(day['raw_daily']) for day in case['days']) != 26040:
        raise ValueError('All pairs must share all21 execution dates')
    checks = {(pair(row), row['ReportDate']):row for row in case['external_fact_ledger']['daily_reconciliation']}
    expected_events = {(key,str(first+timedelta(days=i))) for key in keys for i in range(-21,21)}
    event_map = {(pair(row),row['ReportDate']):row for row in events}
    if len(event_map) != len(events) or set(event_map) != expected_events or set(checks) != expected_events:
        raise ValueError('Business event coverage differs')
    outgoing = defaultdict(int)
    for shipment in case['external_fact_ledger']['shipments']:
        key = pair(shipment); master = mapping[key]
        if shipment['quantity'] % master['PackSize']:
            raise ValueError('Shipment is not a whole retained lot')
        parent = key[0],master['ParentWhCode']
        if parent in keys:
            outgoing[parent,shipment['dispatch_date']] += shipment['quantity']
    for key,event in event_map.items():
        row = checks[key]
        if any(type(event[name]) is not int or event[name] < 0 for name in
               ('requested','realized','lost','parent_outbound','unsupplied')):
            raise ValueError('Invalid business event quantity')
        if (event['realized']+event['lost'] != event['requested']
                or event['realized'] != min(event['requested'],row['opening_stock']+row['receipts'])
                or event['parent_outbound'] != outgoing[key]
                or row['consumption'] != event['realized']+event['parent_outbound']):
            raise ValueError('Parent/child or realized demand conservation differs')
    return {**proof, 'business_event_rows':len(events), 'execution_pair_dates':26040,
            'rlt_distribution':dict(Counter(row['RLT'] for row in masters))}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',',':'))+'\n').encode('utf-8')


def attach_shipments(payload):
    """Apply the approved metadata conventions to these new dated shipments."""
    from tools.prepare_daily_shipment_input import _raw_row, _transporter_index
    case = payload['case']; ledger = case['external_fact_ledger']
    parents = {pair(row):row['ParentWhCode'] for row in case['static_day']['raw_master']}
    directory = case['opening']['consumer_context']['GoodsInTransitTransporterMaster']
    codes = [row['TransporterCode'] for row in directory]
    if len(codes) != 4 or len(set(codes)) != 4:
        raise ValueError('Retained transporter directory differs')
    for day in case['days']:
        today = day['business_date']
        rows = [_raw_row(row,today,parents[pair(row)],codes[_transporter_index(row['shipment_id'],4)])
                for row in ledger['shipments'] if row['dispatch_date'] <= today < row['receipt_date']]
        if sum(row['InTransitQty'] for row in rows) != sum(row['GIT'] for row in day['raw_daily']):
            raise ValueError('Declared raw shipments differ from physical GIT')
        day['shipment_input'] = dict(schema='daily-transit-raw-v1',business_date=today,rows=rows,
            provenance=dict(schema='fresh-rlt4-7-shipment-provenance-v1',
                scenario_sha256=payload['scenario_sha256'],catalogue_sha256=payload['catalogue_sha256'],
                ledger_digest=ledger['shipments_sha256'],directory_digest=digest(directory),
                conventions='docs/DAILY_SHIPMENT_INPUT_CONTRACT.md',rows_digest=digest(rows)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,required=True)
    args = parser.parse_args()
    spec_raw = (ROOT/'baseline/synthetic-temporal-business-v1.json').read_bytes()
    source = json.loads((ROOT/'baseline/synthetic-rlt-4-7-v1.json').read_text())
    full, events = build(Path(source['source_artifact']['path']).read_bytes(),
                         Path(source['catalogue_artifact']['path']).read_bytes(), spec_raw)
    records = {}; trial = {**full, 'case':_reduce_case(full['case'],records)}
    trial['case']['case'] = 'rlt4-7-ten-pair-trial-v1'
    validate_ledger(trial)
    attach_shipments(full)
    attach_shipments(trial)
    args.destination.mkdir(parents=True,exist_ok=False)
    manifest = dict(schema='fresh-synthetic-scenario-artifacts-v1', scenario_sha256=sha(spec_raw),
                    generator_sha256=sha(Path(__file__).read_bytes()), files={})
    reduction = {name:dict(strategy=item['strategy'], source_count=len(item['source']),
        output_count=len(item['output']),source_digest=digest(item['source']),output_digest=digest(item['output']))
        for name,item in records.items()}
    for name,value in [('full-input.json',full),('trial-input.json',trial),('business-ledger.json',events),
                       ('trial-reduction.json',reduction)]:
        raw = encoded(value); (args.destination/name).write_bytes(raw)
        manifest['files'][name] = dict(sha256=sha(raw),bytes=len(raw))
    (args.destination/'manifest.json').write_bytes(encoded(manifest))
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
