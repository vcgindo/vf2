"""Native rationed-report population from computed R1 output, before Pick joins.

The selected processed-input contract preserves all62 source columns. Callers
must supply their own engine's output; this module never reads oracle artifacts.
"""
from collections import defaultdict
from decimal import Decimal

from mta.domain.colours import colour
from mta.domain.virtual_norm import average_positive_norm
from mta.application.r1_report_facts import rationed_leftovers


def _key(row):
    return row['sku_code'], row['location_code']


def _index(rows):
    result = {}
    for row in rows:
        key = _key(row)
        if key in result:
            raise ValueError('Ambiguous computed report position: ' + str(key))
        result[key] = row
    return result


def _int(value):
    return int(Decimal(str(value)))


def rationed_report(source, outputs, sku_descriptions, location_descriptions):
    if source['schema'] != 'r1-current-day-input-v5':
        raise ValueError('Native report currently requires the selected processed-input contract')
    requirements = _index(outputs['r1_requirement'])
    masters = _index(outputs['r1_bpr_master'])
    # The selected R1 importer checkpoint contains effective Norm/structure;
    # unchanged pack metadata belongs to this processed input's importer master.
    importer = _index(source['master_state']['importer_master'])
    positions = _index(source['foundation']['inventory_positions'])
    stocks = {k: _int(v['stock_for_rationing']) for k, v in _index(outputs['r1_stock_balance']).items()}
    normal = _index(outputs['r1_normal_ration'])
    pso = _index(outputs['r1_pso_ration'])
    opening = _index(source['stock_openings'])
    sku_names = {r['sku_code']: r['description'] for r in sku_descriptions}
    loc_names = {r['location_code']: r['description'] for r in location_descriptions}
    children = defaultdict(list)
    for key, master in masters.items():
        children[key[0], master['parent_location_code']].append(_int(master['norm']))
    physical = [{'SKUCode': k[0], 'WhCode': k[1], 'PWh': m['parent_location_code']} for k, m in masters.items()]
    leftovers = rationed_leftovers(
        physical, stocks,
        {k: _int(v['remaining_parent_stock']) for k, v in normal.items() if not v['virtual']},
        {k: _int(v['parent_leftover']) for k, v in pso.items()},
    )
    after_normal = {}
    direct = {}
    for key, row in normal.items():
        parent = key[0], row['parent_location_code']
        remaining = _int(row['remaining_parent_stock'])
        if parent in after_normal and after_normal[parent] != remaining:
            raise ValueError('Ambiguous normal parent leftover')
        after_normal[parent] = remaining
        if row['virtual']:
            if parent in direct:
                raise ValueError('Ambiguous direct allocation')
            direct[parent] = _int(row['final_quantity']) + _int(pso.get(key, {}).get('total_allocation', 0))
    sequence = {name: i for i, name in enumerate(('Black', 'Red', 'Yellow', 'Green', 'Blue', 'White', 'Grey'), 1)}
    child_norms = {key: tuple(values) for key, values in children.items()}
    averages = {}
    def average(key):
        if key not in averages:
            averages[key] = int(average_positive_norm(child_norms.get(key, ())))
        return averages[key]

    result = []
    for key, record in requirements.items():
        master = masters[key]
        parent = key[0], master['parent_location_code']
        parent_record = requirements.get(parent)
        parent_pack = _int(importer[parent]['pack_size']) if parent in importer else 1
        req, virtual, colors = record['requirement'], record['virtual_norm'], record['colours']
        norm = _int(record['effective_norm']['value'])
        vnorm, blue = _int(virtual['value']), _int(virtual['blue_requirement'])
        stock, git = _int(positions[key]['stock_quantity']), _int(positions[key]['goods_in_transit_quantity'])
        physical_color = colour(Decimal(vnorm), Decimal(stock), Decimal(blue - (vnorm - norm)))
        allocation = normal.get(key)
        nqty = _int(allocation['final_quantity']) if allocation else 0
        norm_alloc = min(_int(req['normal_gap']), nqty)
        snp_alloc = _int(pso[key]['total_allocation']) + nqty - norm_alloc if key in pso else 0
        rationed = norm_alloc + snp_alloc
        row = {
            'SKUCode': key[0], 'SKUName': sku_names.get(key[0]),
            'WhCode': key[1], 'WhName': loc_names.get(key[1]),
            'Norm': norm, 'VirtualNorm': vnorm,
            'VirtualNodeNorm': _int(record['direct_virtual_node']['virtual_norm']['value']) if record['direct_virtual_node'] else 0,
            'SpikeThreshold': format(Decimal(req['spike_threshold']), '.2f'),
            'PSOThreshold': format(Decimal(req['pso_threshold']), '.2f'),
            'Stock': stock, 'GIT': git, 'StockForRationing': stocks.get(key, 0),
            'StockForReqCalc': _int(req['stock_for_requirement']),
            'DispatchPen': format(Decimal(colors['dispatch']['penetration']), '.2f'),
            'DispatchColor': colors['dispatch']['band'].title(),
            'DispatchColorSequence': sequence[colors['dispatch']['band'].title()],
            'PhysicalInventoryPen': format(physical_color.penetration, '.2f'),
            'PhysicalInventoryColor': physical_color.band.title(),
            'PhysicalInventoryColorSequence': sequence[physical_color.band.title()],
            'ParentWhCode': parent[1], 'ParentWhName': loc_names.get(parent[1]),
            'ParentNorm': _int(masters[parent]['norm']) if parent in masters else None,
            'Req': _int(req['requirement']),
            'AllocatedForVirtualNormReq': nqty, 'AllocatedForNormReq': norm_alloc,
            'AllocatedForSnPReq': snp_alloc, 'AllocatedForDirectOrders': direct.get(key, 0),
            'RationedReq': rationed, 'PackSize': _int(importer[key]['pack_size']),
            'RationedCasePacks': int(Decimal(rationed) / parent_pack) if parent_pack else 0,
            'LeftoverParentStock': leftovers[key][0], 'LeftoverStock': leftovers[key][1],
            'ParentPackSize': parent_pack, 'IsNormed': norm != 0,
            'DirectSpikeOverdue': _int(req['due_spike']), 'SpikeOverdueAtParent': _int(req['routed_due_spike']),
            'PSO': _int(req['pso']), 'RelPSOAndCNR': _int(req['relevant_pso_cnr']),
            'ResidualChildrenSnP': _int(req['residual_children']), 'SnPToNetOff': _int(req['additional_demand']),
            'SnPNettedOff': _int(req['netted_additional']), 'ResidualSnP': _int(req['residual_additional']),
            'EcoStockForNormReq': _int(req['stock_for_requirement']) + git - _int(req['netted_additional']),
            'NormReq': _int(req['normal_gap']), 'BlueReq': blue,
            'AvgSiblingsNorm': average(parent),
            'AvgChildrenNorm': average(key),
            'ParentStockForNormRationing': stocks.get(parent, 0),
            'ParentStockForSnPRationing': after_normal.get(parent, stocks.get(parent, 0)) if key in pso else 0,
            'ParentStockForRationing': stocks.get(parent, 0),
            'StockPercentageForRationing': _int(opening[key]['stock_percent_reservation']),
            'NormPercentReservation': _int(opening[key]['norm_percent_reservation']),
            'ParentStockPercentageForRationing': _int(opening[parent]['stock_percent_reservation']) if parent in opening else 100,
            'ParentNormPercentReservation': _int(opening[parent]['norm_percent_reservation']) if parent in opening else 0,
        }
        for prefix, kind in (('Tech', 'technical'), ('Eco', 'economic')):
            row[prefix + 'Pen'] = format(Decimal(colors[kind]['penetration']), '.2f')
            row[prefix + 'Color'] = colors[kind]['band'].title()
            row[prefix + 'PenParent'] = format(Decimal(parent_record['colours'][kind]['penetration']), '.2f') if parent_record else None
            row[prefix + 'ColorParent'] = parent_record['colours'][kind]['band'].title() if parent_record else None
        result.append(row)
    return result
