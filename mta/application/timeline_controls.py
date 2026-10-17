"""Connect the accepted phase/season producers to persisted control carry.

The extra tables are closing state, not a new set of daily control answers.
Current-day commands may append only to the source request tables.
"""
from copy import deepcopy

from mta.application.r1_phase_out import collect_phase_out, process_phase_out
from mta.application.r1_phase_in import collect_phase_in, process_phase_in
from mta.application.r1_phase_entry import clear_phase_inputs
from mta.application.r1_seasonality import collect_seasons, process_seasons, apply_seasons
from mta.application.r1_control_diagnostics import phase_exception_rows, failed_force_rows
from mta.domain.control_carry import TABLES, control_stages


EXTRA_TABLES = ('phase_map', 'phase_in_norms', 'phase_exceptions', 'phase_requests',
                'phase_stops', 'phase_in_requests', 'season_status', 'season_requests')
REQUEST_TABLES = ('phase_requests', 'phase_stops', 'phase_in_requests', 'season_requests')
FORCE_CAPTURE_POLICY = 'cohort2-pre-clear-force-v1'


def timeline_control_stages(today, opening_date, state, extra, day, profile, daily, attributes,
                            *, force_alert_capture=None):
    if force_alert_capture is not None and (not isinstance(force_alert_capture, dict)
                                            or force_alert_capture):
        raise ValueError('A new empty force-alert capture sink is required')
    if set(extra) != set(EXTRA_TABLES):
        raise ValueError('Complete persisted phase/season state required')
    commands = day['control_requests']
    if set(commands) != set(REQUEST_TABLES):
        raise ValueError('Only explicit phase/season request feeds are accepted')
    s = {**deepcopy(state), **deepcopy(extra), 'daily': deepcopy(daily),
         'attributes': [{'SKUCode': r['SKUCode'], 'WhCode': r['LocCode'],
                         'PackSize': r['PackSize']} for r in attributes]}
    for name in REQUEST_TABLES:
        s[name].extend(deepcopy(commands[name]))
    timestamp = today + 'T00:00:00'
    stages = (
        ('CollectPhaseOutData.sql', lambda v: collect_phase_out(v, today, timestamp, from_ui=profile['from_ui'])),
        ('ProcessPhaseOut.sql', lambda v: process_phase_out(v, today)),
        ('CollectPhaseInData.sql', lambda v: collect_phase_in(v, today, from_ui=profile['from_ui'], start_percent=profile['start_percent'])),
        ('ProcessPhaseIn.sql', lambda v: process_phase_in(v, today)),
        ('CollectSeasonalityData.sql', lambda v: collect_seasons(v, today)),
        ('ProcessSeasonality.sql', lambda v: process_seasons(v, today)),
        ('ApplySeasonalityNormChanges.sql', lambda v: apply_seasons(v, today)),
    )
    diagnostics = {}
    for name, calculate in stages:
        s = calculate(s)
        if name == 'ProcessPhaseIn.sql':
            diagnostics['phase_exceptions'] = phase_exception_rows(s, timestamp)
        yield name, s, diagnostics
    extras = {n: deepcopy(s[n]) for n in EXTRA_TABLES}
    for name, current in control_stages(today, opening_date, {n: s[n] for n in TABLES},
            profile['force_flags'], day['accepted_feed'], day['new_force_requests']):
        s = {**current, **deepcopy(extras)}
        if name == 'UpdateNormChanges.sql':
            diagnostics['failed_force'] = failed_force_rows(s, today)
            if force_alert_capture is not None:
                # ClearForceNormChange.sql subsequently deletes approved rows.
                # Keep this opt-in projection outside Reports/closing state so
                # ordinary calculation outputs and their digests stay unchanged.
                force_alert_capture.update(deepcopy({
                    'ForceNormChange': s['force_requests'],
                    'DBMMaster': s['dbm_master'],
                    'MasterDataRaw': s['raw_master'],
                }))
        yield name, s, diagnostics
    s = clear_phase_inputs(s, today, history_horizon=profile['history_horizon'])
    yield 'ClearPhaseInPhaseOutData.sql', s, diagnostics
