"""Selected current-day diagnostic rows; never sends email or repairs controls."""
from mta.application.r1_norm_updates import key


def failed_force_rows(state, day):
    masters = {key(r):r for r in state['dbm_master']}
    requests = state['force_requests']
    pending = [r for r in requests if not (key(r) in masters and r['NewNorm'] is not None
               and r['NewNorm'] == masters[key(r)]['Norm'])]
    result = []

    def append(rows, reason):
        nonlocal pending
        result.extend(dict(SKUCode=r['SKUCode'],WhCode=r['WhCode'],Reason=reason) for r in rows)
        identified = {key(r) for r in result}
        pending = [r for r in pending if key(r) not in identified]

    append([r for r in pending if r['Approved'] == 0], 'Not approved')
    append([r for r in requests for raw in state['raw_master'] if key(r)==key(raw) and key(raw) not in masters], 'Record is introduced today')
    append([r for r in pending if not any(key(r)==key(raw) for raw in state['raw_master'])], 'Record does not exist in master data')
    for table,reason in (('phase_out','Phase Out in progress'),('phase_in','Phase In in progress')):
        append([r for control in state[table] for r in pending if key(control)==key(r)],reason)
    append([r for control in state['seasonality'] for r in pending if key(control)==key(r)
            and control['Status'] in (2,3,4,5,6)], 'Seasonality in progress')
    append([r for r in pending for raw in state['raw_master'] if key(r)==key(raw)
            and r['NewNorm'] is not None and raw['Norm'] is not None and r['NewNorm']!=raw['Norm']], 'New Norm is not updated in Master data')
    append([r for log in state['log'] for r in pending if key(log)==key(r)
            and log['NormChangeDate']==day and log['NormChangeReason'] is not None and log['NormChangeReason']<100], 'Norm changed by Suggestion')
    # Selected fixture has no NormCalendar/NewAndDiscontinued source rows.
    append(pending, 'Unknown')
    report = [dict(r,VectorFlowNorm=str(masters[key(r)]['Norm']) if key(r) in masters and masters[key(r)]['Norm'] is not None else 'NA') for r in result]
    return sorted(report,key=lambda r:r['Reason'])


def phase_exception_rows(state, timestamp):
    return [dict(PhaseOutSKUCode=r['PhaseOutSKUCode'],WhCode=r['WhCode'],
                 PhaseInSKUCode=r['PhaseInSKUCode'] or '',
                 TargetNorm='' if r['TargetNorm'] is None else str(r['TargetNorm']),
                 Reason=r['Reason'],Date=r['Log_Date'])
            for r in state['phase_exceptions'] if r['Log_Date']==timestamp]
