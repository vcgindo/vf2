"""Single early producer owner shared by native CSV and JSON daily execution.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from mta.application import daily_finalization
from mta.application.r1_importer_master import process_importer_master
from mta.application.r1_supplier_input import process_supplier_validation, STAGES as SUPPLIER_STAGES
from mta.application.r1_daily_input import process_daily_validation, STAGES as DAILY_STAGES
from mta.application.intake_errors import NativeIntakeRejected
from mta.application.persistent_master import MasterReuse, MasterChange, settings
from copy import deepcopy


def prepare(prior, opening_date, day, profile, identity, *, prepared_master=None, history_changes=None):
    from mta.temporal.chain import entry_inputs
    today=day['business_date']; now=today+'T00:00:00'
    finalization=daily_finalization.configuration(profile)
    if finalization is not None:
        prior=daily_finalization.begin(prior,today,policy=finalization['policy'])
        day=daily_finalization.fresh_feeds(prior,day,policy=finalization['policy'])
    completion=prior['complete'] if finalization is not None else None
    if prepared_master is not None and not isinstance(prepared_master,(MasterReuse,MasterChange)):
        raise ValueError('Accepted master preparation owner differs')
    master_input,daily_input=entry_inputs(prior,opening_date,day,profile,identity,
        _include_master=not isinstance(prepared_master,MasterReuse))
    master=(prepared_master.prepare(master_input) if isinstance(prepared_master,MasterChange) else
            process_importer_master(master_input) if prepared_master is None else prepared_master.result)
    if master['outcome']!='APPLIED':
        raise NativeIntakeRejected('Connected master producer did not apply',
            stage='ValidateAndProcessMaster',rejections=master['tables']['RejectedMaster'])
    if completion is not None:
        daily_finalization.mark(completion,'ValidateAndProcessMaster.sql')
    supplier_additions=[]
    daily_additions=[]
    supplier=process_supplier_validation(day['supplier_feeds'],master,settings(prior),now,
        **({'rejection_additions':supplier_additions} if history_changes is not None else {}))
    supplier_final=supplier[SUPPLIER_STAGES[-1]]['tables']
    if any(value['outcome']=='SQL_ERROR' for value in supplier.values()):
        raise NativeIntakeRejected('Supplier producer failed',stage='SupplierValidation',
            rejections=supplier_final['RejectedMaster'])
    # Daily validation only reads this master producer. The two supplier-owned
    # substitutions get their own mapping; do not copy all immutable masters.
    daily_master={**master, 'tables':dict(master['tables'])}
    for name in ('SiteDescriptionTbl','RejectedMaster'):
        daily_master['tables'][name]=supplier_final[name]
    daily=process_daily_validation(daily_input,daily_master,today,now,
        **({'rejection_additions':daily_additions} if history_changes is not None else {}))
    if any(value['outcome']=='SQL_ERROR' for value in daily.values()):
        raise NativeIntakeRejected('Daily producer failed',stage='DailyValidation',
            rejections=daily[DAILY_STAGES[-1]]['tables']['RejectedMaster'])
    if history_changes is not None:
        if type(history_changes) is not dict or history_changes:
            raise ValueError('Importer history capture requires an empty owned mapping')
        for name,added in (('RetiredNormsTbl',master['retired_events_added']),
                ('RejectedMaster',master['rejects_added']+supplier_additions+daily_additions)):
            history_changes['closing/importer/'+name]=dict(
                opening_count=len(prior['importer'][name]),removed=[],
                additions=deepcopy(added),sorted_prefix=len(added))
    return dict(prior=prior,day=day,master=master,daily_input=daily_input,
        supplier_final=supplier_final,daily=daily,daily_final=daily[DAILY_STAGES[-1]]['tables'],
        finalization=finalization,completion=completion,reused=isinstance(prepared_master,MasterReuse),
        master_work=(prepared_master.work if isinstance(prepared_master,MasterChange) else None))
