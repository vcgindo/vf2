"""Capture overwritten typed DBM report facts; format only after commit.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from mta.domain.dbm_report_dates import report_cutoff

SCHEMA='fresh-deferred-dbm-export-v1'
SOURCES={
    'norm012':('Norm0_1_2ReportDetails','ui_ReportConfigurations'),
    'norm-change':('NormChangeLogTbl','ReasonCodes','LastBatchRunTbl'),
    'norm-history':('NormChangeLogTbl','ReasonCodes','LastBatchRunTbl','SKUDescriptionTbl','SiteDescriptionTbl'),
}


def defer(today,state,kind,*,horizon=None):
    if kind not in SOURCES:raise ValueError('Unknown deferred DBM export producer')
    # Retain configuration/date rejection at the original producer boundary.
    if kind=='norm012':
        from mta.domain.dbm_norm012 import selected_report_configuration
        selected_report_configuration(state['ui_ReportConfigurations'])
    else:report_cutoff(today,state,horizon,inclusive=kind=='norm-change')
    return {**{k:v for k,v in state.items() if k not in ('ReportHeader','ReportRows')},
        '_DeferredExport':dict(schema=SCHEMA,kind=kind,horizon=horizon)}


def render(today,marker,sources):
    if (set(marker)!={'schema','kind','horizon'} or marker['schema']!=SCHEMA
            or marker['kind'] not in SOURCES or set(sources)!=set(SOURCES[marker['kind']])):
        raise ValueError('Deferred DBM source/producer roster differs')
    if marker['kind']=='norm012':
        from mta.domain.dbm_norm012 import export_stage
        result=export_stage(sources)
    elif marker['kind']=='norm-change':
        from mta.domain.dbm_norm_change_report import norm_change_report
        result=norm_change_report(today,sources,marker['horizon'],_owned=True)
    else:
        from mta.domain.dbm_norm_change_history import norm_change_history
        result=norm_change_history(today,sources,marker['horizon'],_owned=True)
    return {name:result[name] for name in ('ReportHeader','ReportRows')}
