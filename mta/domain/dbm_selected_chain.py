"""Complete selected ingestion-starting DBM sequence, preserving every boundary."""
from copy import deepcopy
from mta.domain.dbm_connected import connected_stages
from mta.domain.dbm_delisting import delisting_recommendation
from mta.domain.dbm_postrules import postrule_stages
from mta.domain.dbm_order_summary import update_order_summary
from mta.domain.dbm_norm1_advisory import norm1_advisory
from mta.domain.dbm_norm_change_report import norm_change_report
from mta.domain.dbm_suspension_history import gather_suspension_history
from mta.domain.dbm_norm_change_history import norm_change_history
from mta.domain.dbm_norm012 import norm012_stages
from mta.domain.dbm_daily_cleanup import daily_cleanup


def selected_stages(today, state, facts, configuration=None, report_exceptions=None):
    # Existing retained component receipts use the selected historical profile.
    # Daily production callers must supply the source-pinned batch settings.
    config = configuration
    if config is not None:
        active = lambda name: sum(r['Parameter'] == name and str(r['Value']) == '1'
                                  for r in state['DBMSettingsTbl']) == 1
        if active('NormZeroOneRuleActive'):
            raise ValueError('Conditional Rules7/10/11 require an independently pinned activation profile')
        if config['AutoDBMActive'] != 0 or any(config[f'PhaseOutRecommendation{h}Days'] for h in (30, 60, 90)):
            raise ValueError('Unselected auto-acceptance/phase recommendation profile')
    for name, current in connected_stages(today, state, facts):
        yield name, deepcopy(current)
    if config is None or active('DelistingofNormRuleActive'):
        current = delisting_recommendation(today, current)
        yield 'rule12', deepcopy(current)
    for name, current in postrule_stages(today, current):
        yield name, deepcopy(current)
    for name, calculate in (
        ('order-summary', update_order_summary),
        ('norm1-advisory', norm1_advisory),
        ('norm-change-export', lambda d, s: norm_change_report(d, s, 1 if config is None else config['DBMNormChangeReportHorizon'])),
        ('suspension-history', gather_suspension_history),
        ('norm-change-history', lambda d, s: norm_change_history(d, s, 7 if config is None else config['NormChangeLogHorizon'])),
    ):
        if config is not None and ((name == 'suspension-history' and config['GatherSuspensionHistory'] != 1)
                or (name == 'norm-change-history' and config['ActivateNormChangeLogReport'] != 1)):
            continue
        current = calculate(today, current)
        yield name, deepcopy(current)
    for norm in (0, 1, 2):
        for horizon in ((30, 60, 90) if norm == 0 and config is not None else (30,)):
            if config is not None and config[f'ActivateNorm{norm}Report{horizon}Days'] != 1:
                continue
            excluded = [
                (row['SKUCode'], row['WhCode'])
                for row in (report_exceptions or {}).get('norm012_occurrence_order', [])
                if row['norm'] == norm and row['horizon'] == horizon]
            scope = (report_exceptions or {}).get('norm012_occurrence_order_scope', {})
            exclude_all = (scope.get('all_ambiguous_rows') is True
                           and norm in scope.get('norms', [])
                           and horizon in scope.get('horizons', []))
            for name, current in norm012_stages(
                    today, current, norm, horizon, excluded, exclude_all):
                yield f'norm{norm}-{name}', deepcopy(current)
    current = daily_cleanup(today, current, 370 if config is None else config['DailyConsumptionHorizonDBM'])
    yield 'daily-cleanup', deepcopy(current)


def selected_chain(today, state, facts):
    snapshots = [{'stage': name, 'state': value} for name, value in selected_stages(today, state, facts)]
    return {**snapshots[-1]['state'], 'SelectedDBMStages': snapshots}
