"""Pinned pure DBM consumer joins, not a second calculation engine."""
from itertools import product

def key(row):
    return row['SKUCode'], row.get('WhCode', row.get('WHCode', row.get('LocCode')))

def delivery_history(output, history_end, horizon):
    """History is the computed and carried BTR ledger, including the opening."""
    from datetime import date, timedelta
    if not 1 <= horizon <= 90:
        raise ValueError('horizon must be between 1 and 90 days')
    start = (history_end - timedelta(days=horizon - 1)).isoformat()
    btr = output['BTRFinal'][0]
    result = []
    for row in btr['BPR']:
        day = row['ReportDate'][:10]
        if not start <= day <= history_end.isoformat():
            continue
        populations = (
            [r for r in btr['SKUDescriptionTbl'] if r['SKUCode'] == row['SKUCode']],
            [r for r in btr['SiteDescriptionTbl'] if r['WHCode'] == row['WHCode']],
        )
        for sku, loc in product(*populations):
            result.append({'date': day, 'SKUCode': row['SKUCode'], 'WHCode': row['WHCode'],
                'SKUName': sku['SKUDescription'], 'WHName': loc['WHDescription'],
                **{n: row[n] for n in ('Norm', 'VirtualNorm', 'Stock', 'GIT', 'ParentWhCode', 'DispatchColor', 'DispatchPen')},
                'PhysicalColor': row['PhysicalInventoryColor'], 'PhysicalPen': row['PhysicalInventoryPen'],
                'PipelineColor': row['EcoColor'], 'PipelinePen': row['EcoPen']})
    return sorted(result, key=lambda r: (r['date'], r['SKUCode'], r['WHCode']))

def daily_graph(state, sku, location):
    """BORProcessor's six daily-graph projections over the published DBM state."""
    from datetime import date, timedelta
    from decimal import Decimal

    def numeric(value):
        if value is None:
            return None
        value = Decimal(str(value))
        return int(value) if value == value.to_integral_value() else float(value)

    def selected(table):
        return [r for r in state[table] if key(r) == (sku, location)]

    run_date = state['LastBatchRunTbl'][0]['LastRunDate']
    cutoff = (date.fromisoformat(run_date[:10]) - timedelta(days=90)).isoformat()
    daily = [r for r in selected('DailyConsumption') if r['ReportDate'] >= cutoff]
    suspended = [r for r in selected('SuspendHistory') if r['ReportDate'] >= cutoff]
    pairs = []
    # Preserve FULL OUTER JOIN multiplicity, including dates present on only
    # one side. SQL's INCLUDE_NULL_VALUES retains the missing side's fields.
    for a in suspended:
        matches = [b for b in daily if b['ReportDate'] == a['ReportDate']]
        pairs.extend((a, b) for b in matches or [None])
    pairs.extend((None, b) for b in daily
                 if not any(a['ReportDate'] == b['ReportDate'] for a in suspended))
    stock = []
    for a, b in pairs:
        row = {'dt': (a or b)['ReportDate']}
        row.update({alias: numeric(b[field]) if b else None for alias, field in
                    (('stk', 'Stock'), ('git', 'GIT'), ('cs', 'Consumption'),
                     ('rp', 'Receipts'), ('bz', 'BlueZone'))})
        row.update({alias: numeric(a[field]) if a else None for alias, field in
                    (('rrs', 'RedReasonStockType'), ('grs', 'GreenReasonStockType'),
                     ('rrc', 'RedReasonConsumptionType'), ('grc', 'GreenReasonConsumptionType'))})
        stock.append(row)
    changes = selected('NormChangeLogTbl')
    reasons = state['ReasonCodes']
    return [{
        'StockData': sorted(stock, key=lambda r: r['dt']),
        'NormData': [{'olN': numeric(r['OldNorm']), 'nN': numeric(r['NewNorm']), 'Ndt': r['NormChangeDate']}
                     for r in sorted(changes, key=lambda r: r['NormChangeDate']) if r['NormChangeDate'] >= cutoff],
        'MasterData': [{alias: numeric(r[field]) for alias, field in
                        (('nm', 'Norm'), ('mn', 'MinNorm'), ('rcp', 'RCP'), ('gcp', 'GCP'), ('rlt', 'RLT'))}
                       for r in selected('DBMMaster')],
        'MonitoringData': [{'srrd': a['RedResumeDate'], 'sgrd': a['GreenResumeDate'],
                            'crrd': b['RedResumeDate'], 'cgrd': b['GreenResumeDate']}
                           for a, b in product(selected('SuspendStockType'), selected('SuspendConsumptionType'))],
        'NormChangeHistoryData': [{'olN': numeric(r['OldNorm']), 'nN': numeric(r['NewNorm']),
                                   'nCD': r['NormChangeDate'], 'rsn': reason['Reason']}
                                  for r in sorted(changes, key=lambda r: r['NormChangeDate'], reverse=True)
                                  for reason in reasons if reason['Id'] == r['NormChangeReason']],
        'SuggestionHistoryData': [{'oln': numeric(r['OldNorm']), 'nn': numeric(r['NewNorm']),
                                   'sdate': r['SuggestionDate'], 'rsn': reason['Reason'] if reason else None}
                                  for r in sorted(selected('SuggestionsLog'), key=lambda r: r['SuggestionDate'])
                                  if r['SuggestionDate'] >= cutoff
                                  for reason in [v for v in reasons if v['Id'] == r['Type']] or [None]],
        'RunDate': run_date, 'horizonValue': 90,
    }]

def dbm_rows(state, *, predicate=None):
    """DBMProcessor's full joins and literal attribute aliases, including bags."""
    accepted = {key(r) for r in state['NormAcceptanceTbl']}
    indexes = {}

    def matching(name, key_of, selected):
        if name not in indexes:
            index = {}
            for row in state[name]:
                index.setdefault(key_of(row), []).append(row)
            indexes[name] = index
        return indexes[name].get(selected, [])

    result = []
    for s in state['Suggestions']:
        pair = key(s)
        if pair in accepted:
            continue
        populations = (
            matching('DBMMaster', key, pair),
            matching('SKUDescriptionTbl', lambda r: r['SKUCode'], s['SKUCode']),
            matching('SiteDescriptionTbl', lambda r: r['WHCode'], pair[1]),
            matching('ReasonCodes', lambda r: r['Id'], s['Type']),
            matching('SkuAttributeData', lambda r: r['SKUCode'], s['SKUCode']) or [{}],
            matching('SkuLocAttributeData', lambda r: (r['SKUCode'], r['LocCode']), pair) or [{}],
            matching('LocationAttributeData', lambda r: r['WHCode'], pair[1]) or [{}],
        )
        for m, sku, loc, reason, sa, sla, la in product(*populations):
            row = {'SKUCode': s['SKUCode'], 'SKUName': sku['SKUDescription'].rstrip(),
                'LocCode': key(s)[1], 'LocName': loc['WHDescription'].rstrip(),
                'OldNormValue': m['Norm'], 'NewNormValue': s['NewNorm'], 'Type': s['Type'],
                'Comment': reason['Reason'].rstrip(), 'PWhCode': m['ParentWhCode']}
            for i in range(1, 16):
                row[f'SKUAttribute{i}' if i in (1, 2, 6, 7, 8, 9, 10, 14) else f'c{i}'] = sa.get(f'c{i}') or ''
                row[f'SkuLocAttribute{i}' if i <= 2 else f'sl{i}'] = sla.get(f'c{i}') or ''
                row[f'LocAttribute{i}' if i <= 2 else f'l{i}'] = la.get(f'c{i}') or ''
            for _ in range(predicate(s,m,sa,la,sla) if predicate else 1):
                result.append(row)
    result.sort(key=lambda r: (r['SKUCode'], r['LocCode']))
    return [dict(r, RN=i) for i, r in enumerate(result, 1)]
