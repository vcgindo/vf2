"""Affected daily producer assignments, using the existing native catalogue.

This validates new current generations; it is not a historical storage reader,
sanitizer or second schema catalogue. Native writer-specific rounding remains
at that writer. Validation never rewrites a successful value or its wire kind.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from functools import lru_cache
from contextlib import contextmanager
from contextvars import ContextVar
import json
import math
from pathlib import Path

from mta.application.operational_inputs import typed_value, INTEGER_LIMITS
from mta.row_sequences import is_record_rows
from mta.serialization import digest

CATALOG_DIGEST='84f01ea82866a3898dd134eafac32bca4e35daa193aca9d55da4716074b1e512'
_native_producer=ContextVar('native_daily_output_assignments',default=False)


@contextmanager
def native_assignments(enabled=True):
    """Only the existing native day owns these output assignments."""
    token=_native_producer.set(enabled)
    try:yield
    finally:_native_producer.reset(token)


def producing_native():return _native_producer.get()


def validate_produced_rows(rows,table,**kwargs):
    if producing_native():validate_rows(rows,table,**kwargs)
    return rows


@lru_cache(maxsize=1)
def catalogue():
    value=json.loads((Path(__file__).resolve().parents[1]/'config/production_state_schema_v1.json').read_bytes())
    if digest(value)!=CATALOG_DIGEST:raise ValueError('Pinned native producer catalogue differs')
    return value


def control_fields(table):
    """Declared selected native roster, including empty populations."""
    key='/'.join(catalogue()['bindings']['closing/dbm/'+table])
    return tuple(field for field,_ in catalogue()['tables'][key])


@lru_cache(maxsize=64)
def columns(table):
    native=catalogue()['canonical_columns'].get(table)
    if native is not None:return {column['name']:column for column in native}
    # The existing complete-day supplement binds these two native BPR tables
    # to pinned generic BPR_DBCreation.sql; it already declares their roster.
    # All columns are nullable; native decimals are decimal(13,3), text is
    # nvarchar(50), except the three exact nvarchar(20) columns below.
    if table in ('complete/BPR/LogisticPickList','complete/BPR/PickListDataForTruckFormation'):
        from mta.runtime.complete_daily_state import TABLES
        result={}
        for name,kind in TABLES[table]:
            result[name]=dict(name=name,type=kind,nullable=True,length=(40 if name in
                ('TransportLoadType','DispatchColor') else 100) if kind=='nvarchar' else 0,
                precision=13 if kind=='decimal' else 0,scale=3 if kind=='decimal' else 0)
        return result
    raise ValueError('No declared native producer contract: '+table)


def assigned_decimal(value,precision,scale):
    if isinstance(value,(bool,float)):
        raise ValueError('Exact native decimal required')
    try:number=Decimal(value)
    except (InvalidOperation,TypeError,ValueError):raise ValueError('Exact native decimal required') from None
    limit=Decimal(10)**(precision-scale)
    if not number.is_finite() or abs(number)>=limit:
        raise ValueError('Native decimal range exceeded')
    with localcontext() as context:
        context.prec=max(50,precision+scale+4)
        number=number.quantize(Decimal(1).scaleb(-scale),rounding=ROUND_HALF_UP)
    if abs(number)>=limit:raise ValueError('Native decimal rounding overflow')
    return number


def validate_cell(value,column):
    kind=column['type']
    spec=dict(name=column['name'],type=kind,nullable=column['nullable'])
    if value is not None and kind in INTEGER_LIMITS:
        if isinstance(value,(bool,float)):raise ValueError('Exact native integer required')
        try:number=Decimal(value)
        except (InvalidOperation,TypeError,ValueError):raise ValueError('Exact native integer required') from None
        if not number.is_finite() or number!=number.to_integral_value():raise ValueError('Fraction in assigned native integer')
        value=int(number)
    if kind in ('decimal','numeric'):
        if value is None:
            if not spec['nullable']:raise ValueError('NULL in required column')
            return
        assigned=assigned_decimal(value,column['precision'],column['scale'])
        if Decimal(value)!=assigned:raise ValueError('Missing native decimal assignment scale')
        return
    if kind in ('nvarchar','nchar','varchar','char'):
        length=column['length']
        spec['parameters']='max' if length==-1 else str(length//2 if kind.startswith('n') else length)
    if kind=='numeric':spec['type']='decimal'
    typed_value(value,spec,reserve_null_token=False)


def validate_row(row,table,*,fields=None,stage,ordinal=0):
    from mta.application.accepted_inputs import accepted
    if accepted():
        return
    schema=columns(table)
    selected=tuple(schema) if fields is None else tuple(fields)
    if not selected or len(set(selected))!=len(selected) or any(name not in schema for name in selected):
        raise ValueError('Undeclared native partial producer roster: '+table)
    if not isinstance(row,dict) or set(row)!=set(selected):
        raise ValueError(f'{stage}: {table} occurrence {ordinal} required field roster differs')
    for name in selected:
        try:validate_cell(row[name],schema[name])
        except (ValueError,TypeError,OverflowError,InvalidOperation) as error:
            raise ValueError(f'{stage}: {table}.{name} occurrence {ordinal} value={str(row[name])[:80]!r} '
                f'type={type(row[name]).__name__}: {error}') from error


def validate_rows(rows,table,*,fields=None,stage):
    from mta.application.accepted_inputs import accepted
    if accepted():
        return rows
    if not is_record_rows(rows):raise ValueError('Explicit native producer row population required: '+table)
    # Resolve the declared roster even for an empty population.
    schema=columns(table)
    selected=tuple(schema) if fields is None else tuple(fields)
    if not selected or len(set(selected))!=len(selected) or any(name not in schema for name in selected):raise ValueError('Undeclared native producer fields: '+table)
    for ordinal,row in enumerate(rows):validate_row(row,table,fields=selected,stage=stage,ordinal=ordinal)
    return rows


# Native current tables only. Retained consumption/BPR/log/history generations
# are deliberately absent; their existing producers own new-row validation.
DBM_CURRENT=('DBMMaster','Suggestions','NormAcceptanceTbl','ForcedNormChangeTbl',
    'Seasonality','SuspendStockType','SuspendConsumptionType','SuspendOrderType',
    'OrderDataSummary','Norm1IncreaseSuggestions','Norm0Norm1Norm2Report','Norm0_1_2ReportDetails')
BTR_CURRENT=('BufferTrendReport','BufferTrendReportEcon','BufferTrendDispatch','BufferTrendPhysicalInv',
    'BufferTrendDates','BPPTrendTech','BPPTrendEcon','BPPTrendDispatch','BPPTrendPhysicalInv',
    'BTRSnapshotForUI','BufferTrendGraph','ChronicUnavalabilityData','DBMNormSuggestionsData',
    'LocationAttributeData','SiteDescriptionTbl','SkuAttributeData','SKUDescriptionTbl','SkuLocAttributeData',
    'LastBatchRunTbl')

# A deepcopy is not a new semantic generation. These are actual selected
# writers, excluding retained histories and scratch/report wrappers.
DBM_WRITERS={
    'ingestion':('SuspendCustomSKUTbl','SKULocStandardAttributes'),
    'suspension1-5':('SuspendStockTypePre','SuspendConsumptionTypePre','SuspendOrderTypePre',
        'SuspendMinNormTbl','SuspendStepOneTbl','SuspendStepOneOrderTypeTbl'),
    'suspension6':('SuspendNewSKUTbl',),
    'suspension7':('SuspendAcceptedNormsStockType','NormAcceptanceTbl','SuspendStockType'),
    'suspension8':('SuspendConsumptionType','SuspendAcceptedNormsConsumptionType'),
    'suspension9':('SuspendStockType','ForcedNormChangeTbl','SuspendNormsForceChangedTbl'),
    'suspension10':('SuspendConsumptionType',),
    'suspension11':('SuspendNormsInSleepModeTbl','NormsInSleepModeTbl'),
    'suspension12':('SuspendExistingDisabledNormsTbl',),
    'suspension13':('SuspendSpikeTbl',),'suspension14':('SuspendWhitesTbl',),
    'suspension15':('SuspendSupplyIssueTbl',),'suspension16':('SuspendPhaseOutTbl',),
    'suspension17':('SuspendPhaseInTbl',),'suspension18':('SuspendSeasonalityTbl',),
    'suspension19':('SuspendAggrCommonWithOrderType',),
    'suspension20':('SuspendAggrCommon','SuspendStepOneTbl','SuspendNormsInSleepModeTbl',
        'SuspendExistingDisabledNormsTbl','SuspendPhaseInTbl','SuspendPhaseOutTbl','SuspendSeasonalityTbl','SuspendWhitesTbl'),
    'suspension21':('SuspendAggrStockType','SuspendNewSKUTbl','SuspendSpikeTbl','SuspendSupplyIssueTbl',
        'SuspendNormsForceChangedTbl','SuspendAcceptedNormsStockType'),
    'suspension22':('SuspendAggrConsumptionType','SuspendAcceptedNormsConsumptionType'),
    'suspension23':('SuspendStockType','SuspendAggrCommon','SuspendAggrStockType'),
    'suspension24':('SuspendConsumptionType','SuspendAggrCommon','SuspendAggrConsumptionType'),
    'suspension25':('SuspendOrderType','SuspendAggrCommonWithOrderType'),
    'suspension26':('SuspendInsuffDataPointsTbl','SuspendStockType','SuspendConsumptionType'),
    **{'rule'+str(i):('Suggestions',) for i in (1,2,3,4,5,6,10,11)},
    'rule7':('Suggestions','OrderRuleSummary'),
    'rule12':('Suggestions','DBMDelistingOfNormsWithHits'),
    'discard':('Suggestions',),'reports':('Suggestions',),
    'norm1-advisory':('Norm1IncreaseSuggestions',),'auto-acceptance':('NormAcceptanceTbl',),
    'order-summary':(),'norm-change-export':(),'suspension-history':(),
    'norm-change-history':(),'daily-cleanup':(),
}
NATIVE_ALIASES={'SKULocStandardAttributes':'Importer/SKULocStandardAttributes',
    'ExpediteDispatches':'BPR/ExpediteDispatches'}


def validate_dbm_writer(state,name):
    from mta.application.accepted_inputs import accepted
    if accepted():
        return
    if name in DBM_WRITERS:written=DBM_WRITERS[name]
    elif name.startswith('phase-recommendation-'):written=() # separately typed phase owner
    elif name.startswith(('norm0-','norm1-','norm2-')):
        step=name.rsplit('-',1)[-1]
        written={'data':('Norm0Norm1Norm2Report',),'detail':('Norm0_1_2ReportDetails',),
            'clear':('Norm0Norm1Norm2Report','Norm0_1_2ReportDetails'),'export':()}[step]
    else:raise ValueError('Undeclared native DBM writer: '+name)
    for table in written:
        validate_rows(state[table],NATIVE_ALIASES.get(table,'DBM/'+table),stage='dbm/'+name)


class CurrentGenerations:
    """Operation-local references, released with the owning generator."""
    def __init__(self,tables,role,initial=None):
        self.tables,self.role=tables,role
        self.previous={name:rows for name in tables
            if (rows := (initial or {}).get(name)) is not None}

    def validate(self,state,stage):
        from mta.application.accepted_inputs import accepted
        if accepted():return
        for name in self.tables:
            rows=state.get(name)
            if rows is None or self.previous.get(name) is rows:continue
            validate_rows(rows,self.role+'/'+name,stage=stage)
            self.previous[name]=rows


def validated_new_rows(rows,table,*,stage):
    """Validate only appended rows while the existing history owner streams."""
    from mta.application.accepted_inputs import accepted
    if accepted():
        yield from rows
        return
    for ordinal,row in enumerate(rows):
        if producing_native():validate_row(row,table,stage=stage,ordinal=ordinal)
        yield row
