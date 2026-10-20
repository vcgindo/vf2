"""Strict internal snapshot adapter for evidence-backed Track A node calculations.

One resolved Norm per SKU/location/day, shared by every consumer. Network CNR
rolls up calculated child gaps. Post-route Spike balances and adjusted stock
are explicit inputs, not a claimed implementation of order routing/reservation.
"""
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from mta.domain.models import InventoryPosition, RequirementInput, SkuLocation
from mta.domain.norm_controls import ManualNorm, Seasonality, PhaseOut, PhaseIn, OldSkuNorm, resolve_effective_norm
from mta.domain.demand import AcceptedOrder, ThresholdPolicy, classify_spike, collect_orders, calculate_requirement
from mta.domain.virtual_norm import resolve_virtual_norm
from mta.domain.colours import all_colours
from mta.domain.validation import ZERO, RuleBlocked, identity, number, signed_number


def keys(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError('Unknown or missing input fields: ' + ','.join(required))


def q(value):
    if type(value) not in (str, int):
        raise ValueError('Exact decimal string or integer required')
    return number(Decimal(value), integer=True)


def q_signed(value):
    if type(value) not in (str, int):
        raise ValueError('Exact decimal string or integer required')
    return signed_number(Decimal(value), integer=True)


def json_value(value):
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if isinstance(value, dict):
        return {k: json_value(v) for k, v in value.items()}
    return value


def calculate_track_a(payload, *, allow_negative_stock_for_requirement=False):
    keys(payload, ('schema', 'mode', 'foundation', 'nodes'), ('rationing',))
    if payload['schema'] != 'track-a-v1':
        raise ValueError('Unsupported Track A schema')
    if type(payload['mode']) is not int or payload['mode'] != 0:
        raise RuleBlocked('MTA_MODE', 'Only explicit normal MTA mode 0 is qualified for Track A')
    foundation = payload['foundation']
    if foundation['orders'] or foundation['norm_controls']:
        raise ValueError('Track A orders/controls must have one owner in nodes')
    today = date.fromisoformat(foundation['snapshot']['business_date'])
    masters = {(r['sku_code'],r['location_code']): r for r in foundation['sku_locations']}
    inventory = {(r['sku_code'],r['location_code']): r for r in foundation['inventory_positions']}
    parents = {(r['sku_code'],r['child_location_code']): (r['sku_code'],r['parent_location_code']) for r in foundation['hierarchy']}
    if len(masters) != len(foundation['sku_locations']) or len(inventory) != len(foundation['inventory_positions']) or len(parents) != len(foundation['hierarchy']):
        raise ValueError('Duplicate canonical fact grain')
    if any(date.fromisoformat(r['business_date']) != today for r in inventory.values()):
        raise ValueError('Inventory business date mismatch')
    nodes = {}
    for row in payload['nodes']:
        keys(row, ('sku_code','location_code','policy','controls','orders','stock_for_requirement','routed_due_spike'), ('rationing_priority',))
        key = (identity(row['sku_code']),identity(row['location_code']))
        if key in nodes:
            raise ValueError('Duplicate Track A SKU-location')
        nodes[key] = row
    if not nodes or set(nodes) != set(masters) or set(nodes) != set(inventory):
        raise ValueError('Complete Track A/master/inventory closure required')
    location_codes = {row['location_code'] for row in foundation['locations']}
    children = {key: [] for key in nodes}
    for key, parent in parents.items():
        if key not in nodes or parent[1] not in location_codes:
            raise ValueError('Hierarchy child or parent location outside Track A closure')
        children.setdefault(parent, []).append(key)
    norms, resolving = {}, set()

    def resolve(key):
        if key in norms:
            return norms[key]
        if key in resolving:
            raise ValueError('Cyclic phase-in dependency')
        resolving.add(key)
        master, position = masters[key], inventory[key]
        controls = []
        for c in nodes[key]['controls']:
            kind = c.get('type')
            if kind == 'manual':
                keys(c, ('type','event_id','effective_from','value','kind'))
                controls.append(ManualNorm(c['event_id'],date.fromisoformat(c['effective_from']),q(c['value']),c['kind']))
            elif kind == 'seasonality':
                keys(c, ('type','event_id','start','end','original_norm','target_norm','buildup_days','rlt_days','direction','cap'), ('previous_new_norm',))
                controls.append(Seasonality(c['event_id'],date.fromisoformat(c['start']),date.fromisoformat(c['end']),q(c['original_norm']),q(c['target_norm']),c['buildup_days'],c['rlt_days'],c['direction'],q(c['cap']),None if c.get('previous_new_norm') is None else q(c['previous_new_norm'])))
            elif kind == 'phase_out':
                keys(c, ('type','event_id','started_on','original_norm','previous_new_norm','activation_kind'))
                started = date.fromisoformat(c['started_on'])
                if started > today:
                    raise RuleBlocked('PHASE_FUTURE_ROW','PhaseOutTbl membership requires an already-entered row')
                if c['activation_kind'] in {'DIRECT_NEW','CASCADE_NEW'} and q(c['previous_new_norm']) != q(master['base_norm']):
                    raise ValueError('New phase-out must initialize previous NewNorm from current master Norm')
                completion = None
                if c['activation_kind'] == 'CASCADE_NEW':
                    parent = parents.get(key)
                    parent_controls = nodes[parent]['controls'] if parent in nodes else []
                    if not any(p.get('type') == 'phase_out' and p.get('activation_kind') in {'EXISTING','DIRECT_NEW'} for p in parent_controls):
                        raise RuleBlocked('PHASE_PARENT_NOT_COMPLETE','Cascade requires immediate parent in pre-cascade phase-out population')
                    if resolve(parent).basis != 'PHASE_OUT_FINISHED':
                        raise RuleBlocked('PHASE_PARENT_NOT_COMPLETE','Immediate parent has not completed phase-out')
                    completion = today
                controls.append(PhaseOut(c['event_id'],started,q(position['stock_quantity']),q(position['goods_in_transit_quantity']),q(master['pack_size']),q(c['original_norm']),q(c['previous_new_norm']),c['activation_kind'],completion,key not in parents))
            elif kind == 'phase_in':
                keys(c, ('type','event_id','started_on','old_skus','target_norm','start_percent','previous_new_norm'))
                old = []
                for item in c['old_skus']:
                    keys(item, ('sku_code','original_norm'))
                    old_key = (item['sku_code'],key[1])
                    if old_key not in nodes:
                        raise ValueError('Missing phase-in old SKU at same location')
                    old.append(OldSkuNorm(item['sku_code'],q(item['original_norm']),resolve(old_key)))
                controls.append(PhaseIn(c['event_id'],date.fromisoformat(c['started_on']),tuple(old),None if c['target_norm'] is None else q(c['target_norm']),exact_percent(c['start_percent']),q(c['previous_new_norm'])))
            else:
                raise RuleBlocked('UNKNOWN_NORM_CONTROL','No evidence-backed adapter for control')
        norms[key] = resolve_effective_norm(SkuLocation(*key,q(master['base_norm'])),today,tuple(controls))
        resolving.remove(key)
        return norms[key]

    for key in sorted(nodes):
        resolve(key)
    calculated, classified_orders, visiting = {}, {}, set()

    def requirement(key):
        if key in calculated:
            return calculated[key]
        if key in visiting:
            raise ValueError('Cyclic replenishment hierarchy')
        visiting.add(key)
        child_results = [requirement(child) for child in children[key]]
        row, position = nodes[key], inventory[key]
        phase_out_member = any(c['type'] == 'phase_out' for c in row['controls'])
        keys(row['policy'], ('spike_high','spike_low','pso_high','pso_low','spike_override','pso_override'))
        policy = ThresholdPolicy.from_mapping(row['policy'])
        orders = []
        for order in row['orders']:
            keys(order, ('order_id','quantity','accepted_on','due_date','is_spike'))
            accepted = date.fromisoformat(order['accepted_on'])
            is_spike = order['is_spike']
            if is_spike is None:
                if accepted != today:
                    raise RuleBlocked('ORDER_CLASSIFICATION_HISTORY','Existing order needs its established classification')
                is_spike = classify_spike(q(order['quantity']),norms[key].value,policy)
            orders.append(AcceptedOrder(order['order_id'],*key,q(order['quantity']),accepted,date.fromisoformat(order['due_date']),is_spike))
        demand = collect_orders(tuple(orders),*key,today)
        classified_orders[key] = [{'order_id':o.order_id,'is_spike':o.is_spike,'quantity':o.quantity,
            'due_date':o.due_date,'eligible':not o.is_spike or o.due_date <= today} for o in orders]
        physical = InventoryPosition(*key,today,q(position['stock_quantity']),q(position['goods_in_transit_quantity']))
        result = calculate_requirement(RequirementInput(norms[key],physical),demand,policy,
            cnr=sum((r.normal_gap for r in child_results),ZERO),
            residual_children=sum((r.residual_additional for r in child_results),ZERO),
            routed_due_spike=q(row['routed_due_spike']),
            stock_for_requirement=(q_signed(row['stock_for_requirement']) if allow_negative_stock_for_requirement
                                   else q(row['stock_for_requirement'])),
            allow_negative_stock_for_requirement=allow_negative_stock_for_requirement,
            phase_out=phase_out_member)
        calculated[key] = result
        visiting.remove(key)
        return result

    for key in sorted(nodes):
        requirement(key)
    rows = []
    for key in sorted(nodes):
        norm, result, pos = norms[key], calculated[key], inventory[key]
        parent = parents.get(key)
        peer_norms = tuple(norms[c].value for c in children[parent]) if parent else ()
        pack = q(masters[parent]['pack_size']) if parent in masters else (q(masters[key]['pack_size']) if parent is None else q(1))
        virtual = resolve_virtual_norm(norm.value,result.additional_demand,kind='CHILD' if parent else 'TOP',peer_norms=peer_norms,parent_pack_size=pack)
        colours = all_colours(norm.value,q(pos['stock_quantity']),q(pos['goods_in_transit_quantity']),virtual)
        direct = None
        if children[key] and result.pso + result.due_spike > 0:
            direct_vn = resolve_virtual_norm(ZERO,result.pso+result.due_spike,kind='DIRECT',peer_norms=tuple(norms[c].value for c in children[key]))
            direct = {'business_date':today.isoformat(),'parent_location_code':key[1],
                      'virtual_norm':asdict(direct_vn),'dispatch':asdict(all_colours(ZERO,ZERO,ZERO,direct_vn)['dispatch'])}
        rows.append(json_value({'sku_code':key[0],'location_code':key[1],'business_date':today,
            'effective_norm':asdict(norm),'requirement':asdict(result),'virtual_norm':asdict(virtual),
            'orders':classified_orders[key],
            'colours':{k:asdict(v) for k,v in colours.items()},'direct_virtual_node':direct}))
    return rows


def exact_percent(value):
    from mta.domain.validation import percent
    if type(value) not in (str,int):
        raise ValueError('Exact percentage string or integer required')
    return percent(Decimal(value))
