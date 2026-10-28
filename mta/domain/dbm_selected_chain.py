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
from mta.domain.dbm_norm012 import norm012_stages, report_stage
from mta.domain.dbm_daily_cleanup import daily_cleanup
from mta.domain import dbm_conditional as conditional
from mta.domain.dbm_auto_acceptance import automatic_acceptance
from mta.domain.dbm_phase_recommendation import configuration as phase_configuration, phase_stages


def selected_stages(today, state, facts, configuration=None, report_exceptions=None, *, conditional_settings=None, _owned=False, _defer_exports=False):
    # Existing retained component receipts use the selected historical profile.
    # Daily production callers must supply the source-pinned batch settings.
    from mta.domain.deferred_dbm_exports import defer
    config = configuration
    conditional_active = conditional.enabled(state['DBMSettingsTbl'])
    if conditional_active:
        conditional.configuration(config, conditional_settings)
    if config is not None:
        active = lambda name: sum(r['Parameter'] == name and str(r['Value']) == '1'
                                  for r in state['DBMSettingsTbl']) == 1
        if type(config['AutoDBMActive']) is not int or config['AutoDBMActive'] not in (0, 1):
            raise ValueError('Explicit automatic acceptance flag 0/1 required')
        phase_configuration(config)
    for name, current in connected_stages(today, state, facts, _owned=_owned):
        yield name, current
    if conditional_active:
        for name, calculate in (
                ('rule7', conditional.order_norm_zero_increase),
                ('rule10', lambda d, s: conditional.norm_one_consumption_increase(d, s,
                    multiple_rlt=config[conditional.MULTIPLIERS[0]], importer_vf_settings=conditional_settings)),
                ('rule11', lambda d, s: conditional.norm_two_consumption_decrease(d, s,
                    multiple_rlt=config[conditional.MULTIPLIERS[1]], importer_vf_settings=conditional_settings))):
            current = calculate(today, current)
            yield name, current
    if config is None or active('DelistingofNormRuleActive'):
        current = delisting_recommendation(today, current)
        yield 'rule12', current
    for name, current in postrule_stages(today, current):
        yield name, current
    for name, calculate in (
        ('order-summary', lambda d,s:update_order_summary(d,s,_owned=_owned)),
        ('norm1-advisory', lambda d,s:norm1_advisory(d,s,_owned=_owned)),
        ('auto-acceptance', automatic_acceptance),
        ('norm-change-export', lambda d, s: (defer(d,s,'norm-change',horizon=1 if config is None else config['DBMNormChangeReportHorizon']) if _defer_exports else norm_change_report(d, s, 1 if config is None else config['DBMNormChangeReportHorizon'],_owned=_owned))),
        ('suspension-history', lambda d,s:gather_suspension_history(d,s,_owned=_owned)),
        ('norm-change-history', lambda d, s: (defer(d,s,'norm-history',horizon=7 if config is None else config['NormChangeLogHorizon']) if _defer_exports else norm_change_history(d, s, 7 if config is None else config['NormChangeLogHorizon'],_owned=_owned))),
    ):
        if name == 'auto-acceptance' and (config is None or config['AutoDBMActive'] != 1):
            continue
        if config is not None and ((name == 'suspension-history' and config['GatherSuspensionHistory'] != 1)
                or (name == 'norm-change-history' and config['ActivateNormChangeLogReport'] != 1)):
            continue
        current = calculate(today, current)
        yield name, current
        if name == 'norm1-advisory' and config is not None:
            for stage, current in phase_stages(today, current, config):
                yield stage, current
    for name,current in selected_norm012_stages(today,current,config,report_exceptions,_defer_exports=_defer_exports):
        yield name,current
    current = daily_cleanup(today, current, 370 if config is None else config['DailyConsumptionHorizonDBM'],_owned=_owned)
    yield 'daily-cleanup', current


def selected_norm012_stages(today,state,config=None,report_exceptions=None,*,_defer_exports=False):
    """Actual connected norm-report dispatch, separately bounded for proof."""
    current=state
    disposition = (report_exceptions or {}).get('native_report_disposition')
    if disposition is not None:
        if set(report_exceptions) != {'native_report_disposition'} or config is None or config.get('ActivateNorm0Report30Days') != 1:
            raise ValueError('Native report disposition cannot widen report exceptions')
        from mta.application.native_report_disposition import report_group, disclose_export
        limited_group = report_group(today, state, disposition, norm=0, horizon=30)
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
            if disposition is not None and (norm, horizon) == (0, 30):
                excluded = limited_group
            for name, current in norm012_stages(
                    today, current, norm, horizon, excluded, exclude_all,
                    _defer_export=_defer_exports and disposition is None):
                if disposition is not None and (norm, horizon, name) == (0, 30, 'export'):
                    disclose_export(current, disposition)
                yield report_stage(norm,horizon,name), current


def selected_chain(today, state, facts):
    for _, current in selected_stages(today, state, facts):
        pass
    return current
