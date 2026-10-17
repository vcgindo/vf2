"""Physical BPR construction before dispatch rewrites its colour scratch table."""
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP, localcontext

from mta.domain.dbm_ingestion import _key
from mta.domain.late_bpr_transfer import update_bpr

CONSTRUCTION_TABLES = ('DailyDataForBPR', 'PenetrationAndColor', 'BPRExceptions',
                       'BPR_Table', 'LastBatchRunTbl', 'IntermediateTables')
MIN_PEN = Decimal('-99999999.00')


def unique_values(rows, key, fields):
    result = {}
    for row in rows:
        k, value = key(row), tuple(row[f] for f in fields)
        if k in result and result[k] != value:
            raise ValueError('SOURCE_ORDER_AMBIGUITY: conflicting BPR source ' + str(k))
        result[k] = value
    return result


def _colour(pen, norm, stock, blue):
    if pen >= 100:
        return 'Black'
    if pen >= Decimal('66.67'):
        return 'Red'
    if pen >= Decimal('33.33'):
        return 'Yellow'
    if pen >= 0:
        return 'Green'
    if norm == 0 and stock == 0:
        return 'Grey'
    return 'Blue' if blue > 0 and stock <= norm + blue else 'White'


def construct_stages(today, state, show_norm_zero=True):
    if len(state['LastBatchRunTbl']) != 1 or str(state['LastBatchRunTbl'][0]['LastRunDate'])[:10] != today:
        raise ValueError('BPR construction business date drift')
    current = {name: deepcopy(state[name]) for name in CONSTRUCTION_TABLES}
    masters = defaultdict(list)
    for row in state['BPRMaster']:
        masters[_key(row)].append(row)
    blue = unique_values(state['RequirementBlue'], _key, ('BlueReq',))
    daily = []
    for row in state['BPRDailyConsumption']:
        if str(row['ReportDate'])[:10] != today or row['Stock'] is None:
            continue
        for master in masters[_key(row)]:
            if not show_norm_zero and master['Norm'] == 0:
                continue
            value = blue.get(_key(row), (0,))[0]
            if value is None:
                raise ValueError('NONNULL_CONSTRAINT: DailyDataForBPR.BlueReq')
            daily.append({'SKUCode': row['SKUCode'], 'WHCode': _key(row)[1],
                          'Stock': row['Stock'], 'GIT': row['GIT'], 'BlueReq': value})
    current['DailyDataForBPR'] = daily
    penetration = []
    for row in daily:
        for master in masters[_key(row)]:
            penetration.append({'SKUCode': row['SKUCode'], 'WhCode': row['WHCode'], 'Norm': master['Norm'],
                **{f: row[f] for f in ('Stock', 'GIT', 'BlueReq')},
                'TechPen': '0.00', 'TechColor': 'White', 'TechColorSequence': 0,
                'EcoPen': '0.00', 'EcoColor': 'White', 'EcoColorSequence': 0})
    current['PenetrationAndColor'] = penetration
    current['BPRExceptions'] = []
    yield 'CollectDataForBPR.sql', current

    unique_values(penetration, _key, ('Norm', 'Stock', 'GIT'))
    sequence = unique_values(state['ColorSequence'], lambda r: r['Color'], ('SequenceNo',))
    for row in penetration:
        norm, stock, git = (row[f] for f in ('Norm', 'Stock', 'GIT'))
        with localcontext() as context:
            context.prec = 50
            tech = (Decimal(100) * (norm - stock) / abs(norm)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP) if norm else MIN_PEN
            eco = (Decimal(100) * (norm - stock - git) / abs(norm)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP) if norm else MIN_PEN
        if tech < MIN_PEN or eco < MIN_PEN:
            current['BPRExceptions'].append({f: row[f] for f in ('SKUCode', 'WhCode', 'Norm', 'Stock', 'GIT')})
        for prefix, value, inventory in (('Tech', max(tech, MIN_PEN), stock), ('Eco', max(eco, MIN_PEN), stock + git)):
            band = _colour(value, norm, inventory, row['BlueReq'])
            row[prefix + 'Pen'] = format(value, '.2f')
            row[prefix + 'Color'] = band
            if band in sequence:
                row[prefix + 'ColorSequence'] = sequence[band][0]
    current['IntermediateTables'] = {k: [] for k in current['IntermediateTables']}
    yield 'PhysicalInventoryColour', current

    sku_names = unique_values(state['SKUDescriptionTbl'], lambda r: r['SKUCode'], ('SKUDescription',))
    loc_names = unique_values(state['SiteDescriptionTbl'], lambda r: r['WHCode'], ('WHDescription',))
    attributes = unique_values(state['SkuLocAttributeData'], lambda r: (r['SKUCode'], r['LocCode']),
                               ('FGRMFlag',) + tuple('c' + str(i) for i in range(1, 16)))
    phase_out = {_key(r) for r in state['PhaseOutTbl']}
    phase_in = {_key(r) for r in state['PhaseInTbl']}
    result = []
    for p in penetration:
        for m in masters[_key(p)]:
            key = _key(p)
            row = {'SKUCode': key[0], 'WhCode': key[1], 'ParentWhCode': m['ParentWhCode'], 'Norm': m['Norm'],
                   'SKUName': sku_names.get(key[0], ('',))[0], 'WhName': loc_names.get(key[1], ('',))[0],
                   'ParentName': loc_names.get(m['ParentWhCode'], ('',))[0],
                   'PhaseIn-Out': 2 if key in phase_in else 1 if key in phase_out else 0,
                   **{f: p[f] for f in ('Stock', 'GIT', 'TechPen', 'TechColor', 'TechColorSequence',
                                        'EcoPen', 'EcoColor', 'EcoColorSequence')},
                   'ResidualSnP': -1, 'NormReq': -1, 'BlueReq': None, 'Req': -1, 'RationedQTY': -1, 'LeftoverParentStock': -1}
            attr = attributes.get(key, (None,) * 16)
            row['FGRMFlag'] = attr[0]
            row.update({'SKULocAttr' + str(i): attr[i] for i in range(1, 16)})
            result.append(row)
    current['BPR_Table'] = result
    yield 'GenerateBPR.sql', current


def constructor_then_late(today, state, report):
    """Carry generated BPR into the already-proved late update, without I/O."""
    for _, constructed in construct_stages(today, state):
        pass
    late = update_bpr({'BPR_Table': constructed['BPR_Table'],
                      'BPRDailyConsumption': state['BPRDailyConsumption'],
                      'BPRLastBatchRunTbl': state['LastBatchRunTbl'], 'vf_RationedReqReport': report})
    return constructed, late
