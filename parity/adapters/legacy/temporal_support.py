"""Static SQL bindings only; no modern producer or fixture generator."""
from datetime import date, datetime
from decimal import Decimal
import json

def _json(value):
    if isinstance(value,(date,datetime)): return value.isoformat()
    if isinstance(value,Decimal): return format(value,'f')
    raise TypeError(type(value).__name__)

def _write(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,sort_keys=True,indent=2,default=_json)

SCRIPTS = ('ImportForceNormChange.sql', 'InsertParentOrderTypeSuggestions.sql',
           'UpdateAcceptedNorms.sql', 'UpdateForceChangedNorms.sql', 'UpdateNormChanges.sql', 'ClearForceNormChange.sql')

BINDINGS = {n: ('DBM', t) for n, t in {
    'dbm_master':'DBMMaster', 'suggestions':'Suggestions', 'reason_codes':'ReasonCodes',
    'acceptance':'NormAcceptanceTbl', 'phase_out':'PhaseOutTbl', 'phase_in':'PhaseInTbl',
    'seasonality':'Seasonality', 'forced':'ForcedNormChangeTbl', 'log':'NormChangeLogTbl',
    'triggers':'NormChangeTriggerTbl', 'suggestions_log':'SuggestionsLog',
    'order_summary':'OrderDataSummary', 'suspend_order_type':'SuspendOrderType',
    'dbm_settings':'DBMSettingsTbl', 'last_batch':'LastBatchRunTbl'}.items()}

BINDINGS.update({n: ('Importer', t) for n, t in {
    'importer_master':'MasterData', 'raw_master':'MasterDataRaw', 'force_requests':'ForceNormChange',
    'accepted':'AcceptedNorms', 'upload_log':'UIUploadLogFNC', 'importer_settings':'ImporterSettingsTbl'}.items()})

SHARED_CONTROLS={'dbm_master':'DBMMaster','suggestions':'Suggestions','reason_codes':'ReasonCodes',
    'acceptance':'NormAcceptanceTbl','phase_out':'PhaseOutTbl','phase_in':'PhaseInTbl','seasonality':'Seasonality',
    'forced':'ForcedNormChangeTbl','log':'NormChangeLogTbl','suggestions_log':'SuggestionsLog',
    'order_summary':'OrderDataSummary','suspend_order_type':'SuspendOrderType','dbm_settings':'DBMSettingsTbl'}
