"""Own-state composition of the accepted Norm controls, preserving native fields."""
from copy import deepcopy
from datetime import date

from mta.application.r1_norm_updates import import_forced_norms, apply_norm_updates, clear_force_requests, key
from mta.application.r1_parent_suggestions import insert_parent_suggestions

TABLES = ('dbm_master', 'suggestions', 'reason_codes', 'acceptance', 'phase_out',
          'phase_in', 'seasonality', 'forced', 'log', 'triggers', 'suggestions_log',
          'order_summary', 'suspend_order_type', 'dbm_settings', 'last_batch',
          'importer_master', 'raw_master', 'force_requests', 'accepted', 'upload_log',
          'importer_settings', 'IntermediateTables')


def control_stages(today, opening_date, state, flags, accepted_feed, new_force_requests, *, norm_log_removals=None):
    if set(state) != set(TABLES):
        raise ValueError('Complete prior control tables required')
    if date.fromisoformat(opening_date) >= date.fromisoformat(today):
        raise ValueError('Control predecessor must precede this day')
    if state['last_batch'] != [{'LastRunDate': opening_date + 'T00:00:00'}]:
        raise ValueError('Control predecessor business-date drift')
    ignore = sum(r == {'Parameter':'FNC_MatchMasterNorm','Value':'0'} for r in state['dbm_settings']) == 1
    nms = sum(r == {'Parameter':'NMSActive','Value':'1'} for r in state['importer_settings']) == 1
    if flags != {'from_ui': True, 'ignore_master_norm': ignore, 'nms_active': nms}:
        raise ValueError('Selected control flags must match persisted settings')
    s = deepcopy(state)
    s['last_batch'] = [{'LastRunDate': today + 'T00:00:00'}]
    s['accepted'] = deepcopy(accepted_feed)
    s['force_requests'].extend(deepcopy(new_force_requests))
    s['IntermediateTables'] = {name: [] for name in s['IntermediateTables']}
    early_return = not any(r['Approved'] == 1 for r in s['force_requests'])
    s = import_forced_norms(s, **flags)
    if not early_return:
        for row in s['forced']: row['ChangeDate'] = today
    yield 'ImportForceNormChange.sql', s
    s = insert_parent_suggestions(s, today)
    yield 'InsertParentOrderTypeSuggestions.sql', s

    # Accepted arithmetic has a full accepted master/log/trigger checkpoint and
    # preserves acceptance separately. Forced updates do not mutate acceptance.
    # The export is the actual forced-stage queue before UpdateNormChanges clears.
    dates = {key(r): r['ChangeDate'] for r in s['forced']}
    working = deepcopy(s)
    working['forced'] = [{k: v for k, v in r.items() if k != 'ChangeDate'} for r in working['forced']]
    updated = apply_norm_updates(working, today, norm_log_removals=norm_log_removals)
    accepted = deepcopy(s)
    accepted.update(dbm_master=updated['accepted_checkpoint']['master'],
                    log=updated['accepted_checkpoint']['log'],
                    triggers=updated['accepted_checkpoint']['triggers'], acceptance=updated['acceptance'])
    yield 'UpdateAcceptedNorms.sql', accepted
    for row in updated['forced']: row['ChangeDate'] = dates[key(row)]
    forced = {name: deepcopy(updated[name]) for name in TABLES}
    forced['importer_master'] = deepcopy(s['importer_master'])
    forced['triggers'] = deepcopy(updated['export'])
    yield 'UpdateForceChangedNorms.sql', forced
    exported = {name: deepcopy(updated[name]) for name in TABLES}
    yield 'UpdateNormChanges.sql', exported
    final = clear_force_requests(exported, **flags)
    yield 'ClearForceNormChange.sql', final
