"""Read-only native requirement aggregation; never calculation or acceptance.

Known capability gaps come from the reviewed complete-path obligation map.
Stage blockers stay separate: installation does not inherit publication gates.
No payload mutation, ORM query, owner bootstrap, capture or producer execution.
"""
from datetime import date, timedelta
from decimal import DecimalException
import hashlib
import json
import uuid

from django.core.exceptions import ValidationError
from mta.mdm import initialization_contract as contract
from mta.mdm import initialization_rows as native_rows
from mta.mdm.master_owners import business_fields, typed_field
from mta.runtime import mdm_models, mdm_skuloc_models
from mta.serialization import digest

SCHEMA = 'fresh-production-preflight-v1'
STAGES = ('installation', 'day', 'preparation', 'activation')
MODELS = dict(SkuAttributeData=mdm_models.MdmSkuAttributes,
    SKUDescriptionTbl=mdm_models.MdmSkuDescription,
    LocationAttributeData=mdm_models.MdmLocationAttributes,
    SiteDescriptionTbl=mdm_models.MdmLocationDescription,
    SkuLocAttributeData=mdm_skuloc_models.MdmSkuLocPair,
    MasterData=mdm_skuloc_models.MdmSkuLocMasterPair,
    NMSAllItems=mdm_skuloc_models.MdmSkuLocCurrent)


class PreflightError(ValueError):
    def __init__(self, report, stage):
        self.report, self.stage = report, stage
        super().__init__(json.dumps(report, sort_keys=True))


class Requirements:
    def __init__(self, stage):
        if stage not in STAGES:
            raise ValueError('Explicit native preflight stage required')
        self.stage, self.issues = stage, []

    def add(self, path, owner, code, message, *, category='input', stages=None):
        default_stages = ('installation','day') if self.stage=='installation' else (self.stage,)
        item = dict(path=path, owner=owner, code=code, message=message,
                    category=category, stages=list(stages or default_stages))
        if not any((q['path'], q['owner'], q['code'], q['stages']) ==
                   (item['path'], item['owner'], item['code'], item['stages']) for q in self.issues):
            self.issues.append(item)

    def check(self, path, owner, function, *, code='CONTRACT_INVALID', stages=None, category='input'):
        try:
            function()
        except (ValueError, TypeError, KeyError, OverflowError, DecimalException, ValidationError) as error:
            self.add(path, owner, code, str(error), stages=stages, category=category)

    def object(self, value, path, owner, required, allowed=None):
        if not isinstance(value, dict):
            self.add(path, owner, 'OBJECT_REQUIRED', 'Explicit object required')
            return None
        for key in sorted(set(required) - set(value)):
            self.add(path+'/'+key, owner, 'FIELD_REQUIRED', 'Explicit field/population required')
        for key in sorted(set(value) - set(allowed if allowed is not None else required)):
            self.add(path+'/'+key, owner, 'FIELD_UNKNOWN', 'Field is outside the declared input contract')
        return value

    def bag(self, value, path, owner):
        if not isinstance(value, list):
            self.add(path, owner, 'BAG_REQUIRED', 'Explicit row list required, including empty populations')
            return None
        return value

    def records(self, value, path, owner, *, fields=None, model=None, native_path=None):
        rows = self.bag(value, path, owner)
        if rows is None:
            return
        if model:
            descriptors = {f.name: f for f in business_fields(model)}
            fields = descriptors
        elif native_path:
            try:
                _, fields = native_rows.schema(native_path+'/values', rows)
            except (ValueError, TypeError, KeyError) as error:
                self.add(path, owner, 'POPULATION_SCHEMA_INVALID', str(error))
                return
        for ordinal, row in enumerate(rows):
            at = path+'/'+str(ordinal)
            record = self.object(row, at, owner, fields)
            if record is None:
                continue
            for name in set(record) & set(fields):
                field_path = at+'/'+name
                if model:
                    self.check(field_path, owner,
                        lambda name=name: typed_field(model, descriptors[name], record[name], strict=True))
                else:
                    self.check(field_path, owner,
                        lambda name=name: native_rows.scalar(record[name], fields[name], field_path))
            if native_path and set(record) == set(fields):
                self.check(at, owner, lambda: native_rows.select(record, native_path+'/values', [record]))

    def report(self):
        from mta.presentation.daily_preparation import REQUIRED_LAYERS
        issues = sorted(self.issues, key=lambda q: (q['path'], q['owner'], q['code'], q['category']))
        eligibility = {stage: not any(stage in q['stages'] for q in issues) for stage in STAGES}
        validity = {stage: not any(stage in q['stages'] and q['category'] == 'input' for q in issues)
                    for stage in STAGES}
        return dict(schema=SCHEMA, requested_stage=self.stage, contract_valid=validity[self.stage],
            contract_valid_by_stage=validity, stage_eligibility=eligibility, issues=issues,
            required_outputs=list(REQUIRED_LAYERS)+['planning_summary'],
            overall_handoff_status='UNPROVED_REQUIREMENTS_INCOMPLETE', production_ready=False,
            execution_acceptance=False, verification_obligations=[
                dict(owner='execute_day/finish_run', path='/verification/native_lifecycle',
                     requirement='Real root, late rollback, frozen retry, own persisted successor and full typed/current/queue readback'),
                dict(owner='daily_activation/frontend', path='/verification/application',
                     requirement='Full required layers/summary, scoped API/download/actions and usable frontend'),
                dict(owner='H6/H7/H8', path='/verification/operation',
                     requirement='Portable temporal PowerShell, VPS fresh install/recovery/backup/MTO and target resource proof'),
                dict(owner='order_closing', path='/verification/order_identity',
                     requirement='Approved preserved feed-row identity/counter continuity; do not infer assignment from raw order counts'),
                dict(owner='MDM family workflows', path='/verification/nonempty_workflows',
                     requirement='Required positive approval/action histories; empty populations are not positive workflow proof')])


def require(report, stage):
    if not report['stage_eligibility'][stage]:
        raise PreflightError(report, stage)
    return report


def parse(raw, sha256, collector, path):
    collector.check(path+'/sha256', 'input identity', lambda: contract.sha(sha256, path))
    if not isinstance(raw, bytes):
        collector.add(path, 'input identity', 'BYTES_REQUIRED', 'Exact UTF-8 input bytes required')
        return None
    if hashlib.sha256(raw).hexdigest() != sha256:
        collector.add(path+'/sha256', 'input identity', 'HASH_DIFFERS', 'Input bytes do not match their identity')
    try:
        def nonfinite(value):
            raise ValueError('Nonfinite JSON value')
        return json.loads(raw, object_pairs_hook=contract.object_pairs, parse_constant=nonfinite)
    except (ValueError, UnicodeError) as error:
        collector.add(path, 'input parser', 'JSON_INVALID', str(error))
        return None


def full_capabilities(c):
    # These remain errors for their owning stages, not installation warnings.
    for path, owner, code, message, stages in (
        ('/outputs/bor', 'daily_preparation/chain', 'BOR_SOURCE_UNAVAILABLE',
         'Daily BOR requires producer-owned ReqTopOfBlack and CumulativeTOBlack sources', ('preparation', 'activation')),
        ('/outputs/boroa', 'daily_preparation/chain', 'BOROA_SOURCE_UNAVAILABLE',
         'Daily BOROA requires its owned BORWithOrderAllocation opening source', ('preparation', 'activation')),
        ('/outputs/rrr', 'daily_rrr_storage/colour', 'GENERAL_RRR_SOURCE_UNQUALIFIED',
         'General production colour/full-order RRR source is not qualified by smoke/offline-only receipts', ('preparation', 'activation')),
        ('/outputs/planning_git', 'production_daily/daily_transit', 'SHIPMENT_INTAKE_UNAVAILABLE',
         'Native daily entry has no supplied shipment-ledger intake for required transit sources', ('preparation', 'activation')),
        ('/outputs/activation', 'operational_admission', 'NATIVE_ADMISSION_UNQUALIFIED',
         'General native production admission is not established by fixture/cohort policies', ('activation',))):
        c.add(path, owner, code, message, category='capability', stages=stages)
    from mta.presentation.daily_preparation import COMMANDS
    for layer, command in COMMANDS.items():
        if command in ('prepare_bpr_fixture', 'prepare_guided_history_fixture',
                       'prepare_guided_dbm_fixture', 'prepare_guided_chronic_fixture'):
            c.add('/outputs/'+layer, 'daily_preparation', 'NATIVE_PREPARATION_DISPATCH_UNAVAILABLE',
                'Preparation still dispatches '+command+' outside the exported native command set',
                category='capability', stages=('preparation', 'activation'))


def supported_identifier(c, value, path, owner):
    if value is None:
        return  # Native row/owner validators retain their own NULL semantics.
    from mta.domain.complete_daily_scalars import identifier_sort_key
    c.check(path, owner, lambda: identifier_sort_key(value), code='IDENTIFIER_DOMAIN_UNSUPPORTED',
            category='capability', stages=('day',))


def configuration(c, profile, state, prefix='/configuration'):
    if c.object(profile, prefix, 'configuration',
        ('daily', 'calculation', 'force_flags', 'delivery', 'complete_pick', 'complete_daily', 'daily_publication_config', 'import_non_nms', 'daily_publication'),
        contract.CONTRACT['allowed_profile_keys']) is None:
        return
    for name in ('daily', 'calculation', 'force_flags', 'delivery', 'complete_pick', 'complete_daily', 'daily_publication_config'):
        if name in profile and not isinstance(profile[name], dict):
            c.add(prefix+'/'+name, name, 'OBJECT_REQUIRED', 'Explicit configuration object required')
    shapes = {
        'force_flags': {'from_ui':'bit','ignore_master_norm':'bit','nms_active':'bit'},
        'complete_pick': {'policy':'nvarchar'},
        'complete_daily': {'policy':'nvarchar','consumption_days':'int','remark_days':'int'},
        'daily_publication_config': {'bpr_remark_horizon':'int'},
        'calculation/stock_configuration': {'reservation_type':'int','reservation_for_rationing_only':'bit'},
        'calculation/allocation': {'advance_stock_threshold_percent':'numeric'},
        'delivery/controls': {'from_ui':'bit','start_percent':'numeric','history_horizon':'int'},
    }
    for name,fields in shapes.items():
        slot=profile
        for part in name.split('/'):
            slot=slot.get(part) if isinstance(slot,dict) else None
        if c.object(slot,prefix+'/'+name,name,fields) is not None:
            for field,kind in fields.items():
                if field in slot:
                    if slot[field] is None:
                        c.add(prefix+'/'+name+'/'+field,name,'VALUE_REQUIRED','Configuration NULL is not allowed')
                    else:
                        c.check(prefix+'/'+name+'/'+field,name,lambda field=field,kind=kind: native_rows.scalar(slot[field],kind,field))
    daily = profile.get('daily')
    if isinstance(daily, dict):
        c.object(daily, prefix+'/daily', 'daily input',
            ('settings', 'vf_settings', 'shell_flags', 'distributor_codes', 'vendor_codes', 'vector_dms_codes'),
            ('settings', 'vf_settings', 'shell_flags', 'distributor_codes', 'vendor_codes', 'vector_dms_codes','module_sources'))
        for name in ('settings', 'vf_settings'):
            if name in daily:
                c.records(daily[name], prefix+'/daily/'+name, 'daily input',
                          native_path='input/profile/daily/'+name)
        flags = daily.get('shell_flags')
        from mta.application.r1_daily_input import FLAGS,validate_module_configuration
        if c.object(flags, prefix+'/daily/shell_flags', 'r1_daily_input', FLAGS) is not None:
            c.check(prefix+'/daily/shell_flags','r1_daily_input',
                lambda: validate_module_configuration(flags,daily.get('module_sources')),stages=('day',))
        if isinstance(daily.get('module_sources'),dict):
            sources=daily['module_sources']
            if c.object(sources,prefix+'/daily/module_sources','daily module masters',(),('distributor_norms','vendor_master')) is not None:
                for name,rows in sources.items():
                    c.records(rows,prefix+'/daily/module_sources/'+name,'daily module master',
                        native_path='input/profile/daily/module_sources/'+name)
        modes = [q.get('Value') for q in daily.get('settings', []) if isinstance(q, dict)
                 and q.get('Parameter') == 'MissingDailyDataHandling'] if isinstance(daily.get('settings'), list) else []
        if len(modes) != 1 or modes[0] not in ('1', '2', '3'):
            c.add(prefix+'/daily/settings/MissingDailyDataHandling', 'r1_daily_input', 'DAILY_MODE_REQUIRED',
                'Exactly one supported explicit mode1/2/3 required', stages=('day',))
        for name in ('distributor_codes', 'vendor_codes', 'vector_dms_codes'):
            if name in daily:
                rows = c.bag(daily[name], prefix+'/daily/'+name, 'daily input')
                for i, value in enumerate(rows or []):
                    c.check(prefix+'/daily/'+name+'/'+str(i), 'daily input',
                            lambda value=value: native_rows.scalar(value, 'nvarchar', name))
    calc = profile.get('calculation')
    if isinstance(calc, dict):
        c.object(calc, prefix+'/calculation', 'r1_input',
            ('skus', 'locations', 'stock_openings', 'policies', 'logistics', 'stock_configuration', 'allocation', 'replenishment_exclusions'))
        for name in ('skus', 'locations', 'stock_openings'):
            if name in calc:
                c.records(calc[name], prefix+'/calculation/'+name, 'r1_input',
                    native_path='input/profile/calculation/'+name)
        if isinstance(calc.get('skus'), list):
            for i, row in enumerate(calc['skus']):
                if isinstance(row, dict) and 'sku_code' in row:
                    supported_identifier(c, row['sku_code'], prefix+'/calculation/skus/'+str(i)+'/sku_code', 'complete_daily_scalars')
        if isinstance(calc.get('locations'), list):
            for i, row in enumerate(calc['locations']):
                if isinstance(row,dict) and 'location_code' in row:
                    supported_identifier(c,row['location_code'],prefix+'/calculation/locations/'+str(i)+'/location_code','native Pick partition')
        if 'policies' in calc:
            c.check(prefix+'/calculation/policies', 'r1_input', lambda: native_rows.validate_tree(calc['policies'], 'input/profile/calculation/policies'))
        logistics = calc.get('logistics')
        if c.object(logistics, prefix+'/calculation/logistics', 'r1_input', ('items', 'vehicles', 'location_vehicles')) is not None:
            for name in ('items', 'vehicles', 'location_vehicles'):
                if name in logistics:
                    c.records(logistics[name], prefix+'/calculation/logistics/'+name, 'r1_input',
                              native_path='input/profile/calculation/logistics/'+name)
            for i,row in enumerate(logistics.get('location_vehicles',[])):
                if isinstance(row,dict):
                    supported_identifier(c,row.get('location_code'),prefix+'/calculation/logistics/location_vehicles/'+str(i)+'/location_code','native Pick partition')
    delivery = profile.get('delivery')
    if isinstance(delivery, dict):
        c.object(delivery, prefix+'/delivery', 'delivery', ('site_code', 'batch', 'controls', 'btr_settings'),
                 ('site_code', 'batch', 'controls', 'btr_settings', 'conditional_dbm','btr_history'))
        if 'conditional_dbm' in delivery:
            supplied = c.object(delivery['conditional_dbm'], prefix+'/delivery/conditional_dbm',
                'Importer VFSettings', ('importer_vf_settings',))
            if supplied is not None and 'importer_vf_settings' in supplied:
                c.records(supplied['importer_vf_settings'], prefix+'/delivery/conditional_dbm/importer_vf_settings',
                    'Importer VFSettings', native_path='input/profile/delivery/conditional_dbm/importer_vf_settings')
        batch = delivery.get('batch')
        batch_fields = ('AutoDBMActive', 'DBMNormChangeReportHorizon', 'NormChangeLogHorizon',
            'GatherSuspensionHistory', 'ActivateNormChangeLogReport', 'DailyConsumptionHorizonDBM',
            'PhaseOutRecommendation30Days', 'PhaseOutRecommendation60Days', 'PhaseOutRecommendation90Days',
            'ActivateNorm0Report30Days', 'ActivateNorm0Report60Days', 'ActivateNorm0Report90Days',
            'ActivateNorm1Report30Days', 'ActivateNorm2Report30Days')
        from mta.domain.dbm_conditional import MULTIPLIERS
        from mta.domain.dbm_phase_recommendation import TOLERANCES, configuration as phase_configuration
        if c.object(batch, prefix+'/delivery/batch', 'dbm_selected_chain', batch_fields, (*batch_fields, *MULTIPLIERS, *TOLERANCES)) is not None:
            for name, value in batch.items():
                if name in (*batch_fields, *MULTIPLIERS, *TOLERANCES):
                    c.check(prefix+'/delivery/batch/'+name, 'DBM configuration', lambda value=value: native_rows.scalar(value, 'int', name))
            for horizon in (60,90):
                name=f'ActivateNorm0Report{horizon}Days'
                if name in batch and (type(batch[name]) is not int or batch[name] not in (0,1)):
                    c.add(prefix+'/delivery/batch/'+name,'dbm_selected_chain','REPORT_FLAG_INVALID',
                        'Explicit report flag0/1 required; supported horizons are not disabled',stages=('day',))
            from mta.domain.dbm_report_dates import horizon_days
            for name in ('DBMNormChangeReportHorizon','NormChangeLogHorizon'):
                if name in batch and (name == 'DBMNormChangeReportHorizon' or batch.get('ActivateNormChangeLogReport') == 1):
                    c.check(prefix+'/delivery/batch/'+name,'DBM report cutoff',
                        lambda name=name: horizon_days(batch[name]),stages=('day',))
            if 'AutoDBMActive' in batch and (type(batch['AutoDBMActive']) is not int or batch['AutoDBMActive'] not in (0, 1)):
                c.add(prefix+'/delivery/batch/AutoDBMActive', 'dbm_selected_chain', 'AUTO_DBM_FLAG_INVALID',
                    'Explicit automatic acceptance flag 0/1 required', stages=('day',))
            c.check(prefix+'/delivery/batch', 'Phase recommendation configuration',
                lambda: phase_configuration(batch), stages=('day',))
        settings = delivery.get('btr_settings')
        btr_owner=delivery.get('btr_history')
        btr_owner_rows=None
        if btr_owner is not None:
            if c.object(btr_owner,prefix+'/delivery/btr_history','BTR Importer VFSettings',('importer_vf_settings',)) is not None:
                btr_owner_rows=btr_owner.get('importer_vf_settings')
                c.records(btr_owner_rows,prefix+'/delivery/btr_history/importer_vf_settings','BTR Importer VFSettings',
                    native_path='input/profile/delivery/btr_history/importer_vf_settings')
        btr_fields = ('CaptureDispatchExecutionEfficiency', 'GenerateColorAgeingReport', 'BRAgeColorTolerance',
                      'CARNoColorToleranceDuration', 'NormSuggestion_Upward', 'NormSuggestion_Downward')
        if c.object(settings, prefix+'/delivery/btr_settings', 'btr_finalization', btr_fields,
                    (*btr_fields,'RationingHistoryHorizonBTR')) is not None:
            from mta.domain.btr_finalization import _selected_settings
            if set(btr_fields)<=set(settings):
                c.check(prefix+'/delivery/btr_settings', 'btr_finalization',
                    lambda: _selected_settings(settings,btr_owner_rows), stages=('day',))
    if isinstance(profile.get('complete_daily'), dict):
        from mta.application.daily_finalization import configuration as finalization
        c.check(prefix+'/complete_daily', 'daily_finalization', lambda: finalization(profile))
    if isinstance(state, dict):
        state_requirements(c, state, profile)


def state_requirements(c, state, profile, prefix='/opening/state', *, initial=True):
    from mta.application.daily_finalization import EMPTY_APPROVAL_QUEUES
    dbm = state.get('dbm')
    if isinstance(dbm, dict):
        p = prefix+'/dbm'
        percentages = dbm.get('FirstReplenishmentPercentageTbl')
        if not isinstance(percentages, list) or len(percentages) != 1 or not isinstance(percentages[0], dict) or type(percentages[0].get('ReplenishmentPercentage')) is not int:
            c.add(p+'/FirstReplenishmentPercentageTbl', 'dbm_suspensions.suspend_introductions',
                'REPLENISHMENT_SINGLETON_REQUIRED', 'Exactly one explicit typed replenishment percentage required', stages=('day',))
        settings = dbm.get('DBMSettingsTbl')
        for name in ('SpikeRuleHorizon', 'SpikeRuleParCount'):
            values = [row.get('Value') for row in settings if isinstance(row, dict) and row.get('Parameter') == name] if isinstance(settings, list) else []
            if len(values) != 1:
                c.add(p+'/DBMSettingsTbl/'+name, 'dbm_rules.spike_recommendation', 'SETTING_SINGLETON_REQUIRED',
                      'Exactly one explicit setting required', stages=('day',))
            else:
                c.check(p+'/DBMSettingsTbl/'+name, 'dbm_rules.spike_recommendation', lambda: int(values[0]), stages=('day',))
        from mta.domain.dbm_conditional import enabled as conditional_enabled, configuration as conditional_config
        if isinstance(settings, list) and all(isinstance(q, dict) and {'Parameter','Value'} <= set(q) for q in settings):
            try:
                conditional_active = conditional_enabled(settings)
            except (ValueError, TypeError):
                c.add(p+'/DBMSettingsTbl/NormZeroOneRuleActive', 'dbm_selected_chain', 'CONDITIONAL_ACTIVATION_INVALID',
                      'Conditional activation setting domain differs', stages=('day',))
            else:
                if conditional_active:
                    delivery = profile.get('delivery', {})
                    supplied = delivery.get('conditional_dbm', {}) if isinstance(delivery, dict) else {}
                    vf = supplied.get('importer_vf_settings') if isinstance(supplied, dict) else None
                    batch = delivery.get('batch') if isinstance(delivery, dict) else None
                    c.check('/configuration/delivery/conditional_dbm', 'dbm_conditional',
                        lambda: conditional_config(batch, vf), stages=('day',))
                    if isinstance(vf, list):
                        c.records(vf, '/configuration/delivery/conditional_dbm/importer_vf_settings',
                            'Importer VFSettings', native_path='input/profile/delivery/conditional_dbm/importer_vf_settings')
        if initial and dbm.get('IntermediateTables') != []:
            c.add(p+'/IntermediateTables', 'dbm_suspensions', 'EXPLICIT_SCRATCH_REQUIRED',
                  'Explicit empty initial DBM scratch list required; do not seed calculated rows', stages=('installation', 'day'))
        if not initial and ('IntermediateTables' not in dbm or not isinstance(dbm['IntermediateTables'], list)):
            c.add(p+'/IntermediateTables','own persisted DBM','SCRATCH_SHAPE_REQUIRED',
                  'Required producer-owned DBM scratch list is missing or malformed',stages=('day',))
        batch = profile.get('delivery', {}).get('batch', {}) if isinstance(profile.get('delivery'),dict) else {}
        if isinstance(batch, dict) and any(batch.get(name)==1 for name in (
            'ActivateNorm0Report30Days','ActivateNorm0Report60Days','ActivateNorm0Report90Days','ActivateNorm1Report30Days','ActivateNorm2Report30Days')):
            from mta.domain.dbm_norm012 import selected_report_configuration
            c.check(p+'/ui_ReportConfigurations', 'dbm_norm012.export_stage',
                lambda: selected_report_configuration(dbm['ui_ReportConfigurations']), stages=('day',))
    complete = state.get('complete')
    if isinstance(complete, dict):
        for name in EMPTY_APPROVAL_QUEUES:
            if complete.get(name):
                c.add(prefix+'/complete/'+name, 'daily_finalization.begin', 'SUPPLIER_WORKFLOW_UNQUALIFIED',
                    'Populated complete SOB/MOQ approval workflow is outside the selected qualified domain',
                    category='capability', stages=('day',))
    orders = state.get('orders')
    if isinstance(orders, dict):
        from mta.domain.elephant_orders import validate as validate_elephants
        c.check(prefix+'/orders/ElephantOrders', 'order_closing',
                lambda: validate_elephants(orders.get('ElephantOrders')), stages=('installation','day'))
        identity = orders.get('OrderIdentity')
        valid = (isinstance(identity,list) and len(identity)==1 and isinstance(identity[0],dict)
            and set(identity[0])=={'Seed','Increment','LastValue'} and identity[0]['Seed']==1
            and identity[0]['Increment']==1 and type(identity[0]['LastValue']) is int
            and 1<=identity[0]['LastValue']<=2147483647)
        if not valid:
            c.add(prefix+'/orders/OrderIdentity', 'order_closing', 'ORDER_IDENTITY_REQUIRED',
                'Selected order contract requires one Seed1/Increment1 and valid LastValue', stages=('day',))
    settings = state.get('importer_settings')
    if isinstance(settings, list):
        from mta.application.daily_finalization import ACTIVE_POLICY, POLICY, require_active_settings, require_inactive_qualification
        policy=profile.get('complete_daily',{}).get('policy')
        if policy in (ACTIVE_POLICY,POLICY):
            c.check(prefix+'/importer_settings/NMSActive','native MDM capture',
                lambda:(require_active_settings if policy==ACTIVE_POLICY else require_inactive_qualification)(settings),
                stages=('day',))


def initialization(raw, sha256, *, expected_configuration, expected_recipe):
    c = Requirements('installation')
    value = parse(raw, sha256, c, '/input')
    full_capabilities(c)
    c.add('/day','production_daily','DAILY_INPUT_REQUIRED',
          'Installation inspection has no supplied day facts or persisted day context',stages=('day',))
    if c.object(value, '', 'initialization', ('schema','recipe','configuration','masters','opening','pair_exclusions')) is None:
        return c.report()
    if value.get('schema') != contract.SCHEMA:
        c.add('/schema','initialization','SCHEMA_INVALID','Unknown initialization schema')
    recipe=value.get('recipe')
    if c.object(recipe,'/recipe','extraction recipe',('projection','extractor','version','source_identity')) is not None:
        if recipe.get('projection') != contract.RECIPE:
            c.add('/recipe/projection','extraction recipe','RECIPE_INVALID','Unknown native projection recipe')
        for name in ('extractor','version','source_identity'):
            if name in recipe:
                bounded_text(c,recipe[name],'/recipe/'+name,'extraction recipe',1,256)
    exclusions=c.bag(value.get('pair_exclusions'),'/pair_exclusions','pair exclusions')
    for i,row in enumerate(exclusions or []):
        at='/pair_exclusions/'+str(i)
        if c.object(row,at,'pair exclusions',('SKUCode','WhCode')) is not None:
            for name in ('SKUCode','WhCode'):
                if name in row and row[name] is not None:
                    bounded_text(c,row[name],at+'/'+name,'pair exclusions',0,50)
    for name, expected in (('configuration',expected_configuration),('recipe',expected_recipe)):
        c.check('/'+name+'/digest','input identity',lambda expected=expected: contract.sha(expected,name))
        if name in value and digest(value[name]) != expected:
            c.add('/'+name+'/digest','input identity','HASH_DIFFERS','Supplied object identity differs')
    masters = value.get('masters')
    if c.object(masters, '/masters', 'master owners', contract.MASTER_TABLES) is not None:
        for owner, tables in contract.MASTER_TABLES.items():
            group = masters.get(owner)
            if c.object(group,'/masters/'+owner,owner,tables) is not None:
                for name in tables:
                    if name in group:
                        c.records(group[name],'/masters/'+owner+'/'+name,owner,model=MODELS[name])
                        for i,row in enumerate(group[name] if isinstance(group[name],list) else []):
                            if isinstance(row,dict) and 'SKUCode' in row:
                                supported_identifier(c,row['SKUCode'],'/masters/'+owner+'/'+name+'/'+str(i)+'/SKUCode','complete_daily_scalars')
                            if isinstance(row,dict):
                                for field in ('WHCode','WhCode','LocCode','ParentWhCode','LogisticsLocation'):
                                    if field in row:
                                        supported_identifier(c,row[field],'/masters/'+owner+'/'+name+'/'+str(i)+'/'+field,'native Pick partition')
                            if isinstance(row,dict) and owner=='importer':
                                for field,text_value in row.items():
                                    if isinstance(text_value,str) and not text_value.isascii():
                                        c.add('/masters/'+owner+'/'+name+'/'+str(i)+'/'+field,'r1_importer_master',
                                            'MASTER_TEXT_DOMAIN_UNQUALIFIED','Selected master input requires bounded ASCII text',
                                            category='capability',stages=('day',))
                                if name=='MasterData' and isinstance(row.get('WhCode'),str) and isinstance(row.get('ParentWhCode'),str):
                                    from mta.application.r1_importer_master import _sql_key
                                    if _sql_key(row['WhCode'].strip(' '))==_sql_key(row['ParentWhCode'].strip(' ')):
                                        c.add('/masters/importer/MasterData/'+str(i)+'/ParentWhCode','r1_importer_master',
                                            'SELF_PARENT_INVALID','Existing master rule rejects the same source and destination',stages=('day',))
    opening = value.get('opening')
    if c.object(opening,'/opening','initialization',('identity','date','semantics','norms_provenance','state')) is not None:
        for name,limit in (('identity',128),('norms_provenance',1024)):
            if name in opening:
                bounded_text(c,opening[name],'/opening/'+name,'initialization',1,limit)
        if opening.get('semantics') != 'declared-initial-facts-and-history-v1':
            c.add('/opening/semantics','initialization','SEMANTICS_INVALID','Explicit initial facts/history semantics required')
        if 'date' in opening:
            c.check('/opening/date','initialization',lambda: iso_date(opening['date']))
        state = opening.get('state')
        if c.object(state,'/opening/state','opening owners',contract.STATE_SECTIONS) is not None:
            publication_metadata(c,state.get('publication_context'),'/opening/state/publication_context')
            for section in contract.STATE_SECTIONS:
                if section not in state or section=='publication_context':
                    continue
                if section=='importer_settings':
                    c.records(state[section],'/opening/state/'+section,'importer settings',native_path='input/opening/state/'+section)
                    continue
                required = set(contract.CONTRACT['required_opening_populations'].get(section,()))
                allowed = set(contract.CONTRACT['allowed_opening_populations'].get(section,()))
                if section=='dbm':
                    allowed.add('PhaseOutRecommendation')
                if section=='btr':
                    allowed.add('RationingHistory')
                if section in contract.MASTER_TABLES:
                    required -= set(contract.MASTER_TABLES[section]); allowed -= set(contract.MASTER_TABLES[section])
                if section=='importer':
                    required = allowed = set(contract.PRIOR_TABLES)-set(contract.MASTER_TABLES['importer'])
                if section=='controls':
                    required = allowed = set(contract.CONTROL_TABLES)
                if section=='complete':
                    required |= set(contract.REQUIRED)
                group = state[section]
                if c.object(group,'/opening/state/'+section,section,required,allowed) is None:
                    continue
                for name, rows in group.items():
                    if name not in allowed:
                        continue
                    at='/opening/state/'+section+'/'+name
                    if rows and (section=='dbm' and name not in contract.DBM_CARRY
                        or section=='btr' and name not in contract.BTR_BASE
                        or section=='complete' and name in contract.COMPLETE_OUTPUTS
                        or section=='controls' and name in ('suggestions','forced','triggers','accepted','raw_master')):
                        c.add(at,section,'CALCULATED_OPENING_FORBIDDEN','Initial input cannot seed producer-owned future output')
                    if name=='IntermediateTables':
                        if section=='dbm' and rows!=[] or section=='controls' and rows not in ({},[]):
                            c.add(at,section,'EXPLICIT_SCRATCH_REQUIRED','Explicit empty initial scratch container required')
                    elif name in MODELS and section=='consumer_context':
                        c.records(rows,at,section,model=MODELS[name])
                    else:
                        c.records(rows,at,section,native_path='input'+at)
                    if isinstance(rows,list):
                        for i,row in enumerate(rows):
                            if isinstance(row,dict):
                                for field in contract.HISTORY_DATES & set(row):
                                    if row[field] is not None and isinstance(opening.get('date'),str):
                                        def historical(row=row,field=field):
                                            if date.fromisoformat(str(row[field])[:10])>date.fromisoformat(opening['date']):
                                                raise ValueError('Opening history exceeds its opening date')
                                        c.check(at+'/'+str(i)+'/'+field,section,historical)
    state = opening.get('state') if isinstance(opening,dict) else None
    configuration(c,value.get('configuration'),state)
    # Preserve the authoritative full validator; aggregation never blesses a
    # partial/subset replacement for its installation/semantic requirements.
    c.check('/input','initialization_contract.decode',lambda: contract.decode(raw,sha256,
        expected_configuration=expected_configuration,expected_recipe=expected_recipe), stages=('installation',))
    return c.report()


def daily(raw, sha256, *, frame=None, predecessor=None, initialization_id=None,
          source_digest=None, configuration_digest=None, predecessor_output_digest=None,
          pick_output_root=None, execution_revision=None, retry_capture_id=None, context_issues=()):
    from mta.runtime.production_daily import (SCHEMA as DAY_SCHEMA, FEED_SCHEMA, SOURCE_SCHEMA, SUPPLIER_TABLES,
        DAY_FIELDS, DAY_TABLES, CONTROL_TABLES, decode, working_day, rows as validate_rows)
    c = Requirements('day')
    full_capabilities(c)
    for item in context_issues:
        c.add(**item, stages=('day',))
    value = parse(raw,sha256,c,'/input')
    if not isinstance(execution_revision,str) or not 1<=len(execution_revision)<=80:
        c.add('/execution_revision','execute_day','REVISION_REQUIRED','Explicit bounded revision1–80 characters required')
    if retry_capture_id is not None:
        c.check('/retry_capture_id','frozen MDM capture',lambda:uuid.UUID(str(retry_capture_id)))
    for name,identity in (('initialization_id',initialization_id),):
        c.check('/'+name,'ProductionInitialization',lambda identity=identity:uuid.UUID(str(identity)))
    for name,identity in (('source_digest',source_digest),('configuration_digest',configuration_digest)):
        c.check('/'+name,'ProductionInitialization',lambda identity=identity:contract.sha(identity,name))
    if isinstance(frame,dict):
        configuration(c,frame.get('profile'),None,'/profile')
        opening_frame=frame.get('opening')
        state=opening_frame.get('state') if isinstance(opening_frame,dict) else None
        if not isinstance(opening_frame,dict):
            c.add('/opening','ProductionInitialization','OPENING_REQUIRED','Verified typed opening context required')
        if predecessor is not None:
            state=predecessor.get('closing_state') if isinstance(predecessor,dict) else None
            closing_shape(c,state)
        if isinstance(state,dict) and isinstance(frame.get('profile'),dict):
            state_requirements(c,state,frame.get('profile',{}),
                '/predecessor/closing_state' if predecessor is not None else '/opening/state',initial=predecessor is None)
    else:
        c.add('/initialization','ProductionInitialization','INITIALIZATION_REQUIRED',
              'Verified native initialization context required')
    envelope = {'schema','day','consumer_opening'}
    if isinstance(value,dict) and value.get('schema')==SOURCE_SCHEMA:
        envelope |= {'intake_schema','producer_sources'}
    if c.object(value,'','production_daily',envelope) is not None:
        if value.get('schema') not in (DAY_SCHEMA,FEED_SCHEMA,SOURCE_SCHEMA):
            c.add('/schema','production_daily','SCHEMA_INVALID','Unknown native day schema')
        day = value.get('day')
        intake=value.get('intake_schema',value.get('schema'))
        fields=DAY_FIELDS | ({'raw_master','supplier_feeds'} if intake==FEED_SCHEMA else set())
        if c.object(day,'/day','production_daily',fields) is not None:
            if value.get('schema')==SOURCE_SCHEMA:
                from mta.application.production_source_inputs import validate
                c.check('/producer_sources','native external facts',
                    lambda:validate(value.get('producer_sources'),day.get('business_date')))
            if intake==FEED_SCHEMA:
                c.check('/day/raw_master','external master feed',lambda:validate_rows(day['raw_master'],'Importer/MasterDataRaw','raw_master'))
                feeds={'raw_master':day.get('raw_master')}
                if c.object(day.get('supplier_feeds'),'/day/supplier_feeds','external supplier feeds',SUPPLIER_TABLES) is not None:
                    for name,table in SUPPLIER_TABLES.items():
                        if name in day['supplier_feeds']:
                            feeds['supplier_feeds/'+name]=day['supplier_feeds'][name]
                            c.check('/day/supplier_feeds/'+name,'external supplier feeds',
                                lambda name=name,table=table:validate_rows(day['supplier_feeds'][name],table,name))
                for name,bag in feeds.items():
                    for i,row in enumerate(bag if isinstance(bag,list) else []):
                        if isinstance(row,dict):
                            for field in ('SKUCode','WhCode','WHCode','ParentWhCode','SupplierCode'):
                                if field in row:
                                    supported_identifier(c,row[field],'/day/'+name+'/'+str(i)+'/'+field,'native external feed')
            for name,table in DAY_TABLES.items():
                if name in day:
                    fields=dict(native_rows.STORAGE_TABLES[table])
                    if name=='order_feed': fields.pop('Type')
                    c.records(day[name],'/day/'+name,'daily facts',fields=fields)
                    c.check('/day/'+name,'production_daily',lambda name=name,table=table:validate_rows(day[name],table,name))
                    for i,row in enumerate(day[name] if isinstance(day[name],list) else []):
                        if isinstance(row,dict) and 'SKUCode' in row:
                            supported_identifier(c,row['SKUCode'],'/day/'+name+'/'+str(i)+'/SKUCode','complete_daily_scalars')
                        if isinstance(row,dict) and 'WhCode' in row:
                            supported_identifier(c,row['WhCode'],'/day/'+name+'/'+str(i)+'/WhCode','native Pick partition')
                        if isinstance(row,dict) and name=='raw_daily' and row.get('ReportDate') != day.get('business_date'):
                            c.add('/day/'+name+'/'+str(i)+'/ReportDate','daily facts','DATE_DIFFERS','Daily fact date must match business_date')
            requests=day.get('control_requests')
            if c.object(requests,'/day/control_requests','MDM queues',CONTROL_TABLES) is not None:
                for name,table in CONTROL_TABLES.items():
                    if name in requests:
                        c.records(requests[name],'/day/control_requests/'+name,'MDM queues',fields=dict(native_rows.STORAGE_TABLES[table]))
                        if requests[name]:
                            c.add('/day/control_requests/'+name,'MDM owned queues','OWNED_QUEUE_REQUIRED',
                                  'Daily file cannot replace the source-owned approval queue')
            if day.get('new_force_requests'):
                c.add('/day/new_force_requests','MDM owned queues','OWNED_QUEUE_REQUIRED',
                      'Daily file cannot replace the source-owned Force queue')
            for name in ('phase_controls_input_validation','seasonality_input_validation'):
                if name in day and type(day[name]) is not bool:
                    c.add('/day/'+name,'production_daily','BOOLEAN_REQUIRED','Explicit boolean required')
            consumer=value.get('consumer_opening')
            if consumer is not None and c.object(consumer,'/consumer_opening','consumer owners',('requests','remarks')) is not None:
                from mta.presentation.daily_requests import _typed
                requests=c.bag(consumer.get('requests'),'/consumer_opening/requests','daily_requests')
                for i,row in enumerate(requests or []):
                    c.check('/consumer_opening/requests/'+str(i),'daily_requests',lambda row=row:_typed(row))
                remarks=consumer.get('remarks')
                if c.object(remarks,'/consumer_opening/remarks','ancillary_live',('bpr','bor','boroa')) is not None:
                    if value.get('schema')==SOURCE_SCHEMA:
                        from mta.application.production_source_inputs import validate_initial_remarks
                        c.check('/consumer_opening/remarks','ancillary_live',
                            lambda:validate_initial_remarks(remarks,day.get('business_date')))
                    else:
                        for name in ('bpr','bor','boroa'):
                            if name in remarks and remarks[name]!=[]:
                                c.add('/consumer_opening/remarks/'+name,'ancillary_live','INITIAL_REMARKS_UNSUPPORTED',
                                    'Native H3 entry supports only explicit empty starting remarks',category='capability',stages=('day',))
            opening_date = None
            if isinstance(frame,dict):
                opening_date=opening_frame.get('opening_date') if isinstance(opening_frame,dict) else None
            if predecessor is not None:
                opening_date=predecessor.get('business_date') if isinstance(predecessor,dict) else None
                successor(c,predecessor,initialization_id,source_digest,predecessor_output_digest)
                if value.get('consumer_opening') is not None:
                    c.add('/consumer_opening','daily consumer owners','SUCCESSOR_OPENING_FORBIDDEN','Successor consumes its persisted consumer ownership')
            elif value.get('consumer_opening') is None:
                c.add('/consumer_opening','daily consumer owners','ROOT_CONSUMERS_REQUIRED','Root requires explicit supplied consumer opening')
            if opening_date is not None:
                c.check('/day/business_date','execute_day',lambda: consecutive(opening_date,day.get('business_date')))
            if isinstance(frame,dict) and isinstance(state,dict) and isinstance(state.get('orders'),dict):
                from mta.application.r1_order_input import validate_order_input
                order_state=state['orders']
                source=dict(opening_date=opening_date,opening_identity='native-owned-opening',
                    feed_status=day.get('order_feed_status'),feed_rows=day.get('order_feed'),
                    opening_orders=order_state.get('SpikeOrderData'),closure_history=order_state.get('SpikeOrderClosureHistory'))
                if isinstance(order_state.get('OrderIdentity'),list) and len(order_state['OrderIdentity'])==1:
                    source['identity_last_value']=order_state['OrderIdentity'][0].get('LastValue')
                c.check('/day/order_feed','r1_order_input.validate_order_input',lambda:validate_order_input(source,day.get('business_date')))
            if isinstance(frame,dict) and configuration_digest is not None:
                if digest(frame.get('profile')) != configuration_digest:
                    c.add('/configuration_digest','ProductionInitialization','CONFIGURATION_DIFFERS','Initialization configuration identity differs')
            if isinstance(frame,dict):
                batch=frame.get('profile',{}).get('delivery',{}).get('batch',{})
                if isinstance(batch,dict):
                    from mta.domain.dbm_report_dates import horizon_cutoff
                    for name,inclusive in (('DBMNormChangeReportHorizon',True),('NormChangeLogHorizon',False)):
                        if name in batch and (inclusive or batch.get('ActivateNormChangeLogReport') == 1):
                            c.check('/profile/delivery/batch/'+name,'DBM report cutoff',
                                lambda name=name,inclusive=inclusive: horizon_cutoff(day.get('business_date'),batch[name],inclusive=inclusive))
    c.check('/input','production_daily.decode',lambda:decode(raw,sha256))
    if isinstance(frame,dict):
        c.check('/day','native mode feed ownership',lambda:working_day(decode(raw,sha256),frame['profile']))
    if pick_output_root is not None:
        from pathlib import Path
        if not Path(pick_output_root).is_dir():
            c.add('/pick_output_root','complete_daily_batch_files','OUTPUT_ROOT_REQUIRED','Existing owned output directory required')
    else:
        c.add('/pick_output_root','complete_daily_batch_files','OUTPUT_ROOT_REQUIRED','Explicit existing owned output directory required')
    return c.report()


def operation(stage):
    """Existing-run preparation/activation capability gate, without calculation."""
    if stage not in ('preparation','activation'):
        raise ValueError('Preparation/activation stage required')
    c=Requirements(stage)
    full_capabilities(c)
    return c.report()


def require_native_operation(run, stage):
    """CLI entry barrier for native runs; retain unrelated accepted pipelines."""
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    capture=MdmDailyInputCapture.objects.filter(run=run).select_related('source').first()
    if capture is not None and capture.source.receipt.get('schema')==contract.SOURCE_SCHEMA:
        report=operation(stage)
        require(report,stage)
        return report
    return None


def consecutive(previous, current):
    if date.fromisoformat(current) != date.fromisoformat(previous)+timedelta(days=1):
        raise ValueError('Native day must immediately follow its own opening/predecessor')


def successor(c, parent, initialization_id, source_digest, expected_output_digest):
    fields=('run_id','business_date','kind','status','output_digest','initialization_id','source_digest','capture_status','closing_state')
    if c.object(parent,'/predecessor','own persisted predecessor',fields) is None:
        return
    for name in ('run_id','initialization_id'):
        if name in parent:
            c.check('/predecessor/'+name,'own persisted predecessor',lambda name=name:uuid.UUID(str(parent[name])))
    for name in ('output_digest','source_digest'):
        if name in parent:
            c.check('/predecessor/'+name,'own persisted predecessor',lambda name=name:contract.sha(parent[name],name))
    for name,expected in (('kind','DAILY_CHAIN'),('status','SUCCEEDED'),('capture_status','CONSUMED'),
        ('initialization_id',str(initialization_id)),('source_digest',source_digest),('output_digest',expected_output_digest)):
        if name in parent and parent[name]!=expected:
            c.add('/predecessor/'+name,'own persisted predecessor','PREDECESSOR_DIFFERS',
                  'Predecessor must belong to the same initialization/source and completed consumed output')


def bounded_text(c,value,path,owner,minimum,maximum):
    if not isinstance(value,str) or not minimum<=len(value)<=maximum:
        c.add(path,owner,'TEXT_REQUIRED','Explicit text length '+str(minimum)+'–'+str(maximum)+' required')


def iso_date(value):
    if not isinstance(value,str) or date.fromisoformat(value).isoformat()!=value:
        raise ValueError('ISO date required')


def publication_metadata(c,value,path):
    if c.object(value,path,'publication metadata',('label',)) is not None and 'label' in value:
        bounded_text(c,value['label'],path+'/label','publication metadata',0,1024)


def closing_shape(c,state):
    """Validate persisted successor shapes without initial-only seed restrictions."""
    prefix='/predecessor/closing_state'
    if c.object(state,prefix,'own persisted closing state',contract.STATE_SECTIONS) is None:
        return
    for section in sorted(contract.STATE_SECTIONS & set(state)):
        at=prefix+'/'+section
        if section=='publication_context':
            publication_metadata(c,state[section],at)
            continue
        if section=='importer_settings':
            c.records(state[section],at,section,native_path='input/opening/state/'+section)
            continue
        required=set(contract.CONTRACT['required_opening_populations'].get(section,()))
        allowed=set(contract.CONTRACT['allowed_opening_populations'].get(section,()))
        if section=='dbm': allowed.add('PhaseOutRecommendation')
        if section=='btr': allowed.add('RationingHistory')
        if section=='importer': required=allowed=set(contract.PRIOR_TABLES)
        if section=='controls': required=allowed=set(contract.CONTROL_TABLES)
        if section=='complete': required|=set(contract.REQUIRED)
        group=state[section]
        if c.object(group,at,section,required,allowed) is None:
            continue
        for name in sorted(set(group)&allowed):
            path=at+'/'+name
            if name=='IntermediateTables':
                scratch_shape(c,group[name],path,section)
            elif section=='btr' and name=='ExpediteDispatches':
                # chain.calculate_day owns an ageing projection here. The full
                # expedite report is assembled separately from Pick/masters;
                # its physical table roster is not this predecessor's roster.
                c.records(group[name],path,section,fields={
                    'SKUCode':'nvarchar','WhCode':'nvarchar','BRAge':'int',
                    'BRAgeRedCount':'int','BRAgeBlackCount':'int'})
            elif section=='controls' and name in ('log','phase_in','phase_out','upload_log'):
                # Native control producers use WhCode. Typed storage records
                # that wire spelling while mapping to the physical WHCode.
                _,fields=native_rows.schema('input/opening/state/controls/'+name+'/values',group[name])
                fields={('WhCode' if key=='WHCode' else key):kind for key,kind in fields.items()}
                c.records(group[name],path,section,fields=fields)
            else:
                c.records(group[name],path,section,native_path='input/opening/state/'+section+'/'+name)


def scratch_shape(c,value,path,owner):
    from mta.runtime.relational_state import CATALOG, STORAGE_TABLES
    if isinstance(value,dict):
        entries=list(value.items())
    elif isinstance(value,list):
        entries=[]
        for i,item in enumerate(value):
            if c.object(item,path+'/'+str(i),owner,('table','rows')) is not None and set(item)=={'table','rows'}:
                entries.append((item['table'],item['rows']))
    else:
        c.add(path,owner,'SCRATCH_SHAPE_INVALID','Declared scratch list or dictionary required')
        return
    for i,(table,rows) in enumerate(entries):
        at=path+'/'+str(i)
        binding=CATALOG['bindings'].get('scratch/'+table) if isinstance(table,str) else None
        if binding is None:
            c.add(at+'/table',owner,'SCRATCH_TABLE_UNKNOWN','Undeclared persisted scratch table')
            continue
        c.records(rows,at+'/rows',owner,fields=dict(STORAGE_TABLES['/'.join(binding)]))


def frozen_retry(capture,leaves,request,parent,today,revision,snapshot,nms,horizon):
    """Aggregate pure predicates used by the existing locked retry boundary."""
    errors=[]
    expected=(('status',capture.run.status,'FAILED'),('capture_status',capture.status,'CAPTURED'),
        ('active_leaf',leaves,[capture.run_id]),('request_digest',capture.request_digest,request),
        ('predecessor',capture.run.predecessor_id,parent.pk if parent else None),
        ('business_date',capture.run.business_date.isoformat(),today))
    for name,actual,wanted in expected:
        if actual!=wanted: errors.append(('/retry_capture_id/'+name,'Frozen retry '+name+' differs'))
    if capture.run.execution_revision==revision:
        errors.append(('/retry_capture_id/execution_revision','Retry requires a distinct execution revision'))
    if not isinstance(snapshot,dict) or not snapshot:
        errors.append(('/retry_capture_id/snapshot','Frozen capture snapshot required'))
        return errors
    if snapshot.get('revision_digest')!=capture.revision_digest:
        errors.append(('/retry_capture_id/snapshot/revision_digest','Frozen capture revision differs'))
    if snapshot.get('nms_active')!=nms:
        errors.append(('/retry_capture_id/snapshot/nms_active','Frozen NMSActive differs'))
    config=snapshot.get('configuration')
    if not isinstance(config,dict) or config.get('task_status_log_horizon')!=horizon:
        errors.append(('/retry_capture_id/snapshot/configuration/task_status_log_horizon','Frozen task horizon differs'))
    return errors
