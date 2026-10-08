"""BOR operation inputs from immutable live capture and typed daily state."""
from copy import deepcopy

from mta.application import operational_bor as bor
from mta.domain.complete_daily_scalars import ascii_equal
from mta.runtime.operational_attempts import configuration_value
from mta.runtime.operational_opening import opening_rows
from mta.runtime.operational_source import read_source
from mta.runtime.services import read_outputs

COLOR_SEQUENCE = [dict(Color=color, SequenceNo=i) for i, color in enumerate(
    ('Black', 'Red', 'Yellow', 'Green', 'Blue', 'White', 'Grey'), 1)]


def _project(owner, name, fields):
    if not isinstance(owner, dict) or not isinstance(owner.get(name), list):
        raise ValueError('Explicit typed BOR population absent: ' + name)
    if any(not isinstance(row, dict) or not set(fields) <= set(row) for row in owner[name]):
        raise ValueError('Typed BOR population fields absent: ' + name)
    return [{field: deepcopy(row[field]) for field in fields} for row in owner[name]]


def bor_inputs(owner):
    """No trace fallback, accepted-run backfill, or inferred empty population."""
    config = configuration_value(owner.configuration)
    for name, expected in (('IsMTOEnvironment', '0'), ('BOROAHistoryHorizon', '90'),
                           ('RRROAHistoryHorizon', '90')):
        if [row['value'] for row in config['settings'] if row['name'] == name] != [expected]:
            raise ValueError('Explicit generic BOR setting required: ' + name)
    captured = read_source(owner.run)
    output = read_outputs(owner.run)
    if config['bindings'].get('bor_color_sequence') != COLOR_SEQUENCE:
        raise ValueError('Explicit canonical BPR ColorSequence seed required')
    if len(output.get('ClosingState', [])) != 1 or len(output.get('BPRReports', [])) != 1:
        raise ValueError('One typed BOR closing and BPR owner required')
    closing, final = output['ClosingState'][0], output['BPRReports'][0]
    rationed = _project(final, 'vf_RationedReqReport',
        tuple('LeftoverParentStock' if name == 'LeftOverParentStock' else name
              for name in bor.RATIONED_FIELDS))
    for row in rationed:
        row['LeftOverParentStock'] = row.pop('LeftoverParentStock')
    # ReqInColorBand starts from vf_ReqCalculation without DISTINCT. The modern
    # band producer emits one row per requirement identity; retain every captured
    # occurrence here. AdvAllocDone is the native stock-only source-location SUM,
    # not the combined stock/GIT advances or any current report total.
    requirements = []
    for row in captured['requirement_bands']:
        amounts = [item['allocated_quantity'] for item in captured['advance_stock_allocations']
                   if ascii_equal(item['sku_code'], row['SKUCode'])
                   and ascii_equal(item['source_location_code'], row['WhCode'])]
        requirements.append(dict(SKUCode=row['SKUCode'], WhCode=row['WhCode'],
                                 AdvAllocDone=bor._int(sum(amounts))))
    current_rrr = opening_rows(owner, 'RRR_OrderAllocation')
    if current_rrr != []:
        raise ValueError('Generic disabled RRR producer requires approved empty population')
    return dict(
        collect=dict(bpr_master=_project(closing.get('bpr'), 'BPRMaster', bor.BPR_MASTER_FIELDS),
            sob_data=_project(closing.get('supplier'), 'SOBData', bor.SOB_FIELDS),
            moq_data=_project(closing.get('supplier'), 'MOQData', bor.MOQ_FIELDS),
            requirements=captured['requirement_bands'],
            rationed_report=rationed,
            bpr_table=_project(final, 'BPR_Table', bor.BPR_TABLE_FIELDS)),
        report=dict(color_sequence=deepcopy(config['bindings']['bor_color_sequence']),
            sku_descriptions=_project(closing.get('importer'), 'SKUDescriptionTbl', bor.SKU_DESCRIPTION_FIELDS),
            site_descriptions=_project(closing.get('importer'), 'SiteDescriptionTbl', bor.SITE_DESCRIPTION_FIELDS),
            requirement_rows=requirements, is_mto_environment=0),
        bor_history=opening_rows(owner, 'BOR_OrderAllocationHistory'),
        current_rrr=current_rrr, rrr_history=opening_rows(owner, 'RRR_OrderAllocationHistory'))
