"""Finite stable BOR join ingredients; scopes, paging and remarks remain live."""
import json
from pathlib import Path
from mta.presentation.bor_contract import FIELDS as SOURCE_FIELDS, recipe_digest as source_recipe
from mta.serialization import digest

SOURCES={
    'B':'reports/bpr/vf_RationedReqReport', 'S':'closing/dbm/SKULocStandardAttributes',
    'C':'closing/importer/SkuAttributeData','D':'closing/importer/LocationAttributeData',
    'E':'closing/importer/SkuLocAttributeData','F':'closing/importer/SKUDescriptionTbl',
    'G':'closing/importer/SiteDescriptionTbl',
}
_catalog=json.loads((Path(__file__).resolve().parents[2]/'baseline/production-state-schema.json').read_text())
_b_names=('DispatchColorSequence TechColor EcoColor Req GIT Stock SpikeThreshold PSOThreshold '
          'StockForReqCalc DispatchPen PhysicalInventoryColor DispatchColor DirectSpikeOverdue '
          'SpikeOverdueAtParent PSO RelPSOAndCNR ResidualChildrenSnP SnPToNetOff SnPNettedOff '
          'ResidualSnP EcoStockForNormReq NormReq BlueReq Norm VirtualNorm EcoPen ParentWhCode').split()
_b_types=dict(_catalog['tables']['BPR/vf_RationedReqReport'])
FIELDS={
    'A':{n:('bigint' if k=='int' else 'text') for n,k in SOURCE_FIELDS['SupplierDispatchReq'].items()},
    'B':{n:('numeric' if _b_types[n] in ('decimal','numeric') else 'bigint' if _b_types[n]=='int' else 'text') for n in _b_names},
    'S':{'Tags':'text'},
    'C':{**{f'SL{i}':'text' for i in range(1,6)},**{f'c{i}':'text' for i in range(1,16)}},
    'D':{**{f'LL{i}':'text' for i in range(1,6)},**{f'c{i}':'text' for i in range(1,16)},'LocationType':'text'},
    'E':{f'c{i}':'text' for i in range(1,16)},
    'F':{'SKUDescription':'text'},'G':{'WHDescription':'text'},'H':{'WHDescription':'text'},
    'I':{'SOB':'float'},'J':{'MOQ':'bigint'},
}
OWNERS=tuple(FIELDS)


def field_name(owner,name): return owner.lower()+'_'+name.lower()


def recipe_digest():
    return digest(dict(version=1,source=source_recipe(),sources=SOURCES,fields=FIELDS,
        joins='source-left-requirement-standard-attributes-descriptions-sob-moq',
        ordinals=OWNERS,comparison="lower(rtrim(value::text,' '))"))


def production_recipe_digest():
    from mta.presentation.bor_contract import production_recipe_digest as native_source_recipe
    return digest(dict(version=1,source=native_source_recipe(),sources=SOURCES,fields=FIELDS,
        joins='source-left-requirement-standard-attributes-descriptions-sob-moq',
        ordinals=OWNERS,comparison="lower(rtrim(value::text,' '))"))
