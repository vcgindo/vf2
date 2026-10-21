"""Pure native-row bridges from this engine's current R1 populations.

No database/trace reads and no requirement/ration recalculation. ReqCalculation
and BOR expose only the fields consumed by the complete-day producers: they are
explicitly NOT complete native table images. Full-row qualification remains a
controller obligation, including native join occurrence order.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from decimal import Decimal

from mta.presentation.rrr import pick_rows, CATALOG
from mta.domain.complete_daily_scalars import ascii_equal
from mta.domain.ordinal_lookup import OrderedIndex

SOURCES = {
    'supplier': ('Scripts/BPR/Ration_Scripts/GenSupplierWiseReq.sql',
                 'fae0668e77fb3e149f62301f4e5e3cda1c1b546180a66f8262ca899644f16a9b'),
    'pick': ('Scripts/BPR/Ration_Scripts/GenerateBifurcationOfRationedReq.sql',
             '8da7fde0a88fd29a8c1f3af0d92ff578be50262f1b5605be8421a1686c45f0b5'),
    'requirement': ('Scripts/BPR/Ration_Scripts/CalculateReq.sql',
                    '587c367323409081b9d1bf8050c23f166ab829a1f1f947cfe7d37bc5cd3902bf'),
    'bor': ('Scripts/BPR/OrderAllocationReports/CollectBOR_OrderAllocationData.sql',
            'e06d22c31b0b51b6ba375c4bdf8ddeac52806d6e0b5b1c362a77dd8d3b4b18da'),
}
SUPPLIER_MAP = dict(SKUCode='sku', WHCode='location', SupplierCode='supplier',
    OriginalReq='original_requirement', DispatchReq='dispatch_requirement',
    ReqTopOfRed='to_red', ReqTopOfYellow='to_yellow', ReqTopOfGreen='to_green', ReqTopOfBlue='to_blue')
BANDS = dict(TOR_B='to_black', TOR_R='to_red', TOY='to_yellow', TOG='to_green', TOBlue='to_blue')
PICK_FIELDS = tuple(name for name, _ in CATALOG['tables']['BPR/vf_RationedReqReport']) + tuple(BANDS) + (
    'PostPipelineInventoryPen', 'PostPipelineInventoryColor')
REQ_FIELDS = ('SKUCode', 'WhCode', 'ParentWhCode', 'Norm', 'Stock', 'GIT', 'VirtualNorm')
BOR_FIELDS = ('SKUCode', 'WhCode', 'DispatchColor')
VIRTUAL_ALIASES = {
    'ParentWhCode': 'WhCode', 'ParentWhName': 'WhName', 'ParentNorm': 'Norm',
    'TechPenParent': 'TechPen', 'TechColorParent': 'TechColor',
    'EcoPenParent': 'EcoPen', 'EcoColorParent': 'EcoColor',
    'Req': '0', 'AllocatedForVirtualNormReq': '0', 'AllocatedForNormReq': '0',
    'AllocatedForSnPReq': '0', 'RationedReq': '0', 'RationedCasePacks': '0',
    'LeftoverParentStock': 'LeftoverStock', 'LeftoverStock': '0',
    'ParentPackSize': 'PackSize', 'IsNormed': '0', 'SpikeOverdueAtParent': '0',
    'ResidualChildrenSnP': '0', 'AvgSiblingsNorm': 'AvgChildrenNorm', 'AvgChildrenNorm': '0',
    'ParentStockPercentageForRationing': 'StockPercentageForRationing',
    'ParentNormPercentReservation': 'NormPercentReservation',
}
MISSING_OWNERS = {
    'vf_ReqCalculation': {
        'coverage': 'PostBTR consumed fields only',
        'missing': 'Full final native row: OriginalTotalReq, advance-allocation and RelPnC intermediate fields '
                   'are not all exposed by r1_requirement; no complete native row owner exists here.'},
    'BORWithOrderAllocation': {
        'coverage': 'PostBTR consumed fields only',
        'missing': 'Full native INSERT/UPDATE materializer, including ParentLeftoverStock, DispatchPen and '
                   'supplier-parent-conditioned Order*UnsatisfiedPercentage updates; r1_bor_oa alone '
                   'does not expose that complete table image.'},
}


def _int(value, *, nullable=False):
    if value is None and nullable:
        return None
    if type(value) not in (int, str, Decimal):
        raise ValueError('Native integral output required')
    number = Decimal(value)
    if not number.is_finite() or number != number.to_integral_value() or not -2147483648 <= number <= 2147483647:
        raise ValueError('Native SQL int output differs or overflows')
    return int(number)


def _join(left, right, fields, equal):
    return all(left[a] is not None and right[b] is not None and equal(left[a], right[b]) for a, b in fields)


def _occurrences(source, rows, prefix):
    """Case is the existing R1 producer's occurrence identity, never a row key."""
    lookup = {}
    for ordinal, row in enumerate(source):
        case = row.get('case', prefix + str(ordinal + 1))
        identity = (case, row['sku_code'], row['location_code'], row['supplier'])
        if identity in lookup:
            raise ValueError('Ambiguous supplier occurrence identity; no invented representative')
        lookup[identity] = ordinal
    used, result = set(), []
    for row in rows:
        identity = (row['case'], row['sku'], row['location'], row['supplier'])
        if identity not in lookup or identity in used:
            raise ValueError('Calculated supplier occurrence lacks unique actual input lineage')
        used.add(identity)
        result.append(lookup[identity])
    return result


def supplier_dispatch(*, sourcing, bor, bpr_master, sku_loc_attributes, equal):
    """Native GenSupplierWiseReq final INSERT; all 28 columns and join bags.

    Quantities come from the existing r1_bor owner. Only its native final INSERT
    projection, topmost join, attribute LEFT JOIN and four cumulative aliases
    are materialized here. Output sequence follows supplied BOR occurrences.
    """
    source_ordinals = _occurrences(sourcing, bor, 'r1_bor_')
    # Candidate bags retain source ordinals; the native residual still owns
    # SQL NULL/comparison semantics and short-circuit/error behaviour.
    with OrderedIndex(bpr_master, key=lambda r: (r['SKUCode'], r['WHCode']),
                      enabled=equal is ascii_equal) as parents:
        topmost = [(i, row) for i, row in enumerate(bpr_master) if not any(
            _join(row, parent, (('SKUCode', 'SKUCode'), ('ParentWhCode', 'WHCode')), equal)
            for parent in parents.candidates_for(row, 'SKUCode', 'ParentWhCode'))]
    rows, lineage = [], []
    with OrderedIndex(topmost, key=lambda item: (item[1]['SKUCode'], item[1]['WHCode']),
                      enabled=equal is ascii_equal) as masters, OrderedIndex(
            sku_loc_attributes, key=lambda r: (r['SKUCode'], r['LocCode']),
            enabled=equal is ascii_equal) as attribute_index:
        return _supplier_rows(bor, source_ordinals, masters, attribute_index, equal, rows, lineage)


def _supplier_rows(bor, source_ordinals, masters, attribute_index, equal, rows, lineage):
    for calculated_ordinal, (item, source_ordinal) in enumerate(zip(bor, source_ordinals)):
        base = {native: deepcopy(item[modern]) if native in ('SKUCode', 'WHCode', 'SupplierCode')
                else _int(item[modern]) for native, modern in SUPPLIER_MAP.items()}
        for master_ordinal, master in masters.candidates((base['SKUCode'], base['WHCode'])):
            if not _join(base, master, (('SKUCode', 'SKUCode'), ('WHCode', 'WHCode')), equal):
                continue
            attributes = [(i, row) for i, row in attribute_index.candidate_items((base['SKUCode'], base['WHCode'])) if _join(
                base, row, (('SKUCode', 'SKUCode'), ('WHCode', 'LocCode')), equal)] or [(None, None)]
            for attribute_ordinal, attr in attributes:
                row = dict(base)
                row.update({f'SKULocAtt{i:02}': None if attr is None else deepcopy(attr[f'c{i}']) for i in range(1, 16)})
                for name, fields in (
                        ('CumulativeTOR', ('ReqTopOfRed',)),
                        ('CumulativeTOY', ('ReqTopOfRed', 'ReqTopOfYellow')),
                        ('CumulativeTOG', ('ReqTopOfRed', 'ReqTopOfYellow', 'ReqTopOfGreen')),
                        ('CumulativeTOB', ('ReqTopOfRed', 'ReqTopOfYellow', 'ReqTopOfGreen', 'ReqTopOfBlue'))):
                    row[name] = _int(sum(base[field] for field in fields))
                rows.append(row)
                lineage.append(dict(output_ordinal=len(rows)-1, calculated_ordinal=calculated_ordinal,
                    sourcing_ordinal=source_ordinal, bpr_master_ordinal=master_ordinal,
                    attribute_ordinal=attribute_ordinal, case=item['case']))
    return rows, lineage


def pick_report(*, rationed, bands):
    """Full Pick INSERT image before separately owned post-ration updates."""
    rows = pick_rows(rationed, bands)
    for row in rows:
        # Exact native INSERT literals, not absent-population defaults.
        row['PostPipelineInventoryPen'] = None
        row['PostPipelineInventoryColor'] = None
        if row['WhCode'] == row['ParentWhCode']:
            # The existing presentation adapter leaves these physical aliases;
            # the canonical virtual INSERT copies the receiving-node values.
            row['ParentStockPercentageForRationing'] = row['StockPercentageForRationing']
            row['ParentNormPercentReservation'] = row['NormPercentReservation']
        if type(row['IsNormed']) not in (bool, int) or row['IsNormed'] not in (0, 1):
            raise ValueError('Canonical Pick IsNormed bit differs')
        row['IsNormed'] = bool(row['IsNormed'])
        if set(row) != set(PICK_FIELDS):
            raise ValueError('Full native Pick INSERT column roster differs')
    return rows


def requirement_projection(*, source, requirements, bpr_master, equal):
    rows = []
    for item in requirements:
        key = dict(SKUCode=item['sku_code'], WhCode=item['location_code'])
        masters = [m for m in bpr_master if _join(key, m, (('SKUCode', 'SKUCode'), ('WhCode', 'WHCode')), equal)]
        positions = [p for p in source['foundation']['inventory_positions']
                     if p['sku_code'] == item['sku_code'] and p['location_code'] == item['location_code']]
        if len(masters) != 1 or len(positions) != 1:
            raise ValueError('Partial Req projection requires its unique actual master/physical-stock owner')
        rows.append(key | dict(ParentWhCode=deepcopy(masters[0]['ParentWhCode']),
            Norm=_int(item['effective_norm']['value']), Stock=_int(positions[0]['stock_quantity']),
            GIT=_int(positions[0]['goods_in_transit_quantity']), VirtualNorm=_int(item['virtual_norm']['value'], nullable=True)))
    return rows


def bor_oa_projection(*, supplier_openings, bor):
    source_ordinals = _occurrences(supplier_openings, bor, 'r1_bor_oa_')
    spellings = {name: name.title() for name in ('BLACK', 'RED', 'YELLOW', 'GREEN', 'BLUE', 'WHITE')}
    rows, lineage = [], []
    for ordinal, (item, source_ordinal) in enumerate(zip(bor, source_ordinals)):
        if item['dispatch_colour'] not in spellings:
            raise ValueError('Canonical BOR dispatch colour spelling unavailable')
        rows.append(dict(SKUCode=item['sku'], WhCode=item['location'], DispatchColor=spellings[item['dispatch_colour']]))
        lineage.append(dict(output_ordinal=ordinal, calculated_ordinal=ordinal,
                            supplier_opening_ordinal=source_ordinal, case=item['case']))
    return rows, lineage


def field_maps():
    def entry(kind, expression, owner):
        path, pin = SOURCES[kind]
        return dict(canonical_source=path, source_sha256=pin, expression=expression, modern_owner=owner)
    supplier = {native: entry('supplier', 'TempSuppDispatchReq.' + native, 'r1_bor.' + modern)
                for native, modern in SUPPLIER_MAP.items()}
    supplier.update({f'SKULocAtt{i:02}': entry('supplier', f'SkuLocAttributeData.c{i} LEFT JOIN',
                                            f'actual BPR SkuLocAttributeData.c{i}') for i in range(1, 16)})
    for name, expression in [('CumulativeTOR', 'ReqTopOfRed'), ('CumulativeTOY', 'ReqTopOfRed+ReqTopOfYellow'),
            ('CumulativeTOG', 'ReqTopOfRed+ReqTopOfYellow+ReqTopOfGreen'),
            ('CumulativeTOB', 'ReqTopOfRed+ReqTopOfYellow+ReqTopOfGreen+ReqTopOfBlue')]:
        supplier[name] = entry('supplier', expression, 'canonical final INSERT alias over r1_bor bands')
    pick = {field: entry('pick', 'physical: vf_RationedReqReport.' + field + '; virtual: '
                        + VIRTUAL_ALIASES.get(field, 'vf_RationedReqReport.' + field),
                        'mta.presentation.rrr.pick_rows') for field in PICK_FIELDS}
    pick['AllocatedForDirectOrders'] = entry('pick', 'physical: UPDATE 0; virtual: AllocatedForDirectOrders',
                                            'actual rationed report / canonical literal')
    for field, modern in BANDS.items():
        pick[field] = entry('pick', field + ' final band UPDATE', 'r1_ration_bifurcation.' + modern)
    for field in ('PostPipelineInventoryPen', 'PostPipelineInventoryColor'):
        pick[field] = entry('pick', 'NULL in both INSERTs', 'canonical literal before post-ration updates')
    for field, expression in [('ParentStockPercentageForRationing', 'virtual: StockPercentageForRationing'),
                              ('ParentNormPercentReservation', 'virtual: NormPercentReservation')]:
        pick[field] = entry('pick', 'physical: vf_RationedReqReport.' + field + '; ' + expression, 'actual rationed report aliases')
    req = {field: entry('requirement', field, owner) for field, owner in zip(REQ_FIELDS,
        ('r1_requirement.sku_code', 'r1_requirement.location_code', 'actual BPRMaster.ParentWhCode',
         'r1_requirement.effective_norm.value', 'actual source inventory.stock_quantity',
         'actual source inventory.goods_in_transit_quantity', 'r1_requirement.virtual_norm.value'))}
    bor = {field: entry('bor', field, owner) for field, owner in zip(BOR_FIELDS,
        ('r1_bor_oa.sku', 'r1_bor_oa.location', 'r1_bor_oa.dispatch_colour canonical spelling'))}
    return dict(SupplierDispatchReq=supplier, vf_PickListReport=pick, vf_ReqCalculation=req, BORWithOrderAllocation=bor)


def materialize_inputs(*, source, calculated, rationed, bpr_master, sku_loc_attributes, equal):
    if source.get('schema') != 'r1-current-day-input-v5':
        raise ValueError('Explicit selected actual R1 input required')
    if 'supplier_openings' not in source:
        raise ValueError('Explicit own supplier opening required; no sourcing fallback')
    supplier, supplier_lineage = supplier_dispatch(sourcing=source['sourcing'], bor=calculated['r1_bor'],
        bpr_master=bpr_master, sku_loc_attributes=sku_loc_attributes, equal=equal)
    bor, bor_lineage = bor_oa_projection(supplier_openings=source['supplier_openings'], bor=calculated['r1_bor_oa'])
    return dict(populations=dict(SupplierDispatchReq=supplier,
        vf_PickListReport=pick_report(rationed=rationed, bands=calculated['r1_ration_bifurcation']),
        vf_ReqCalculation=requirement_projection(source=source, requirements=calculated['r1_requirement'],
                                                 bpr_master=bpr_master, equal=equal),
        BORWithOrderAllocation=bor), field_maps=field_maps(),
        lineage=dict(SupplierDispatchReq=supplier_lineage, BORWithOrderAllocation=bor_lineage),
        missing_full_native_owners=deepcopy(MISSING_OWNERS))
