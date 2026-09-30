"""Selected UpdateBPR -> GetDailyData connection over full table populations."""
from copy import deepcopy

from mta.domain.dbm_ingestion import _key, import_daily_observations

FIELD_MAP = {'ResidualSnP': 'ResidualSnP', 'NormReq': 'NormReq', 'BlueReq': 'BlueReq',
             'Req': 'Req', 'RationedQTY': 'RationedReq', 'LeftoverParentStock': 'LeftoverParentStock'}
TABLES = ('BPR_Table', 'BPRDailyConsumption', 'BPRLastBatchRunTbl', 'vf_RationedReqReport',
          'DBMMaster', 'DailyConsumption', 'LastBatchRunTbl', 'DailyDataRaw',
          'DistributorTransactions', 'VendorTransactions', 'IntermediateTables')


def update_bpr(state):
    """Retain all unassigned fields/dates and target multiplicities.

    An undefined SQL UPDATE source is rejected, never resolved with a tie rule.
    A NULL daily BlueZone is a constraint failure, never zero-filled.
    """
    result = deepcopy(state)
    dates = state['BPRLastBatchRunTbl']
    if len(dates) != 1:
        raise ValueError('A single BPR business date is required')
    today = str(dates[0]['LastRunDate'])[:10]
    sources = {}
    for row in state['vf_RationedReqReport']:
        key = _key(row)
        values = tuple(row[field] for field in FIELD_MAP.values())
        if key in sources and sources[key] != values:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting rationed report fields')
        sources[key] = values
    for row in result['BPR_Table']:
        if _key(row) in sources:
            row.update(zip(FIELD_MAP, sources[_key(row)]))
    blue_index = list(FIELD_MAP).index('BlueReq')
    for row in result['BPRDailyConsumption']:
        if str(row['ReportDate'])[:10] == today and _key(row) in sources:
            value = sources[_key(row)][blue_index]
            if value is None:
                raise ValueError('NONNULL_CONSTRAINT: BPR DailyConsumption.BlueZone')
            row['BlueZone'] = value
    return result


def transfer_stages(today, state):
    if set(state) != set(TABLES):
        raise ValueError('Late transfer opening roster drift')
    for table in ('BPRLastBatchRunTbl', 'LastBatchRunTbl'):
        if len(state[table]) != 1 or str(state[table][0]['LastRunDate'])[:10] != today:
            raise ValueError('Late transfer business date drift')
    current = update_bpr(state)
    yield 'update-bpr', deepcopy(current)
    current['DailyConsumption'] = import_daily_observations(
        today, current['DailyConsumption'], current['DailyDataRaw'], current['DBMMaster'],
        current['BPRDailyConsumption'], current['DistributorTransactions'], current['VendorTransactions'])
    current['IntermediateTables'] = {name: [] for name in current['IntermediateTables']}
    yield 'get-daily-data', deepcopy(current)


def late_transfer(today, state):
    stages = list(transfer_stages(today, state))
    result = deepcopy(stages[-1][1])
    # Persist nested scratch rows as named populations, like the existing chain.
    result['IntermediateTables'] = [{'table': name, 'rows': rows}
                                   for name, rows in sorted(result['IntermediateTables'].items())]
    result['TransferStages'] = [{'stage': name, 'state': output} for name, output in stages]
    return result
