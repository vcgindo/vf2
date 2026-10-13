"""ImportSpikeOrders -> CalculateDD closing state, including SQL identity state.

The ordinary/Spike/whole-quantity Elephant paths reuse the accepted producers.
Generated identity ordering uses
the explicitly approved production feed-row rule, not canonical parity.
"""
from copy import deepcopy
from mta.evidence import snapshot, final_stage
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING

from mta.application.r1_order_input import reconcile_order_feed
from mta.domain.order_identity import MAX_KEY, next_keys

TABLES = ('BPRMaster', 'DBMMaster', 'AdditionalMasterData', 'SpikeOrderData',
          'SpikeOrderClosureHistory', 'NewSpikeOrders', 'ElephantOrders',
          'OrderIdentity', 'LastBatchRunTbl', 'PSOData', 'IntermediateTables')


def key(*values):
    return tuple(v.rstrip(' ').upper() for v in values)


def indexed(rows, warehouse='WhCode'):
    result = {}
    for row in rows:
        k = key(row['SKUCode'], row[warehouse])
        if k in result:
            raise ValueError('Duplicate order master join is outside passing parity')
        result[k] = row
    return result


def order_stages(today, opening_date, state, feed_status, feed):
    """State is one initial opening or the actual verified prior closing state."""
    if set(state) != set(TABLES):
        raise ValueError('Complete order closing state required')
    if date.fromisoformat(opening_date) >= date.fromisoformat(today):
        raise ValueError('Order predecessor must precede this run')
    if state['LastBatchRunTbl'] != [{'LastRunDate': opening_date + 'T00:00:00'}]:
        raise ValueError('Order predecessor business-date drift')
    identity = state['OrderIdentity']
    if (len(identity) != 1 or set(identity[0]) != {'Seed', 'Increment', 'LastValue'}
            or identity[0]['Seed'] != 1 or identity[0]['Increment'] != 1
            or type(identity[0]['LastValue']) is not int
            or not 1 <= identity[0]['LastValue'] <= MAX_KEY):
        raise ValueError('Explicit selected SQL identity counter required')
    counter = identity[0]['LastValue']
    if any(r['OrderKey'] > counter for r in state['SpikeOrderData']):
        raise ValueError('Order identity counter precedes an existing key')
    masters = indexed(state['BPRMaster'], 'WHCode')
    attributes = indexed(state['AdditionalMasterData'])
    dbm = indexed(state['DBMMaster'])
    from mta.domain.elephant_orders import acceptance
    accepted, elephants = acceptance(state['ElephantOrders'], state['SpikeOrderData'],
                                     attributes, masters, today, counter)
    counter += len(accepted)
    source = {'opening_date': opening_date, 'opening_identity': 'own-closing-order-state',
              'feed_status': feed_status, 'feed_rows': deepcopy(feed),
              'opening_orders': state['SpikeOrderData'], 'closure_history': state['SpikeOrderClosureHistory']}
    # Counter ownership survives an empty table and the deletion of prior rows.
    source['identity_last_value'] = counter
    joined = []
    for k, row in masters.items():
        if k not in attributes:
            raise ValueError('Order closing requires its computed additional master')
        joined.append({**attributes[k], 'SKUCode': row['SKUCode'], 'WhCode': row['WHCode'], 'Norm': row['Norm'],
                       'SpikeThreshold': attributes[k]['SpikeThreshold'],
                       'ElephantOrderCapping': attributes[k]['ElephantOrderCapping']})
    imported = reconcile_order_feed(source, joined, today, accepted_orders=accepted, elephant_orders=elephants)
    counter = max([counter]+[r['OrderKey'] for r in imported['orders']])
    s = deepcopy(state)
    s.update(SpikeOrderData=imported['orders'], SpikeOrderClosureHistory=imported['closure_history'],
             ElephantOrders=imported['elephant_orders'],
             NewSpikeOrders=imported['new_spikes'], PSOData=deepcopy(feed),
             LastBatchRunTbl=[{'LastRunDate': today + 'T00:00:00'}],
             IntermediateTables={name: [] for name in state['IntermediateTables']})
    for rows in (s['SpikeOrderData'], s['SpikeOrderClosureHistory']):
        for row in rows:
            row['IsSpike'], row['IsElephant'] = bool(row['IsSpike']), bool(row['IsElephant'])
    s['OrderIdentity'] = [{'Seed': 1, 'Increment': 1, 'LastValue': counter}]
    yield 'ImportSpikeOrders.sql', snapshot(s)

    # Literal selected SQL level loop: one INSERT SELECT per level. Its anti-join
    # intentionally omits WhCode. All candidates see the pre-insert population.
    pending = []
    feed_ordinals = {key(r['OrderID'],r['SKUCode'],r['WhCode']):i for i,r in enumerate(feed)}
    accepted = {}
    existing = {key(r['CustomerOrderId'], r['SKUCode']) for r in s['SpikeOrderData']}
    max_level = max((r['WhLevel'] for r in attributes.values()), default=-1)
    for level in range(max_level, -1, -1):
        for row in s['NewSpikeOrders']:
            a = attributes.get(key(row['SKUCode'], row['WhCode']))
            if a is not None and a['WhLevel'] == level:
                pending.append({**row, '_feed_ordinal':feed_ordinals[key(row['CustomerOrderId'],row['SKUCode'],row['WhCode'])],
                                'CurrentWhCode': row['WhCode'], 'Norm': 0, 'RLT': 0,
                                'FirstServicingWhCode': None, 'DueDate': None})
        for row in pending:
            k = key(row['SKUCode'], row['CurrentWhCode'])
            master, attr = masters.get(k), attributes.get(k)
            if master is None:
                row['FirstServicingWhCode'] = row['CurrentWhCode']
            else:
                row['Norm'] = master['Norm']
            if row['FirstServicingWhCode'] is None and attr is not None:
                threshold = (Decimal(str(attr['SpikeThreshold'])) / 100 * row['Norm']).to_integral_value(rounding=ROUND_CEILING)
                if row['Qty'] <= threshold:
                    row['FirstServicingWhCode'] = row['CurrentWhCode']
            if row['FirstServicingWhCode'] is not None:
                minimum = date.fromisoformat(today) + timedelta(days=row['RLT'])
                expected = row['CustomerExpectedDate']
                row['DueDate'] = max(minimum, date.fromisoformat(expected)).isoformat() if expected else minimum.isoformat()
        candidates = [r for r in pending if r['FirstServicingWhCode'] is not None
                      and key(r['CustomerOrderId'], r['SKUCode']) not in existing]
        for row in candidates:
            accepted[row['_feed_ordinal']] = row
        # Keep the original per-level anti-join semantics (including omitted
        # WhCode); only numerical identities are deferred to feed-row order.
        existing.update(key(r['CustomerOrderId'],r['SKUCode']) for r in candidates)
        pending = [r for r in pending if r['FirstServicingWhCode'] is None]
        for row in pending:
            parent = dbm.get(key(row['SKUCode'], row['CurrentWhCode']))
            if parent is not None:
                row['CurrentWhCode'] = parent['ParentWhCode']
                row['RLT'] += parent['RLT']
    resolved = [accepted[i] for i in range(len(feed)) if i in accepted]
    values = next_keys(counter, len(resolved))
    for row, value in zip(resolved, values):
        s['SpikeOrderData'].append({
            'OrderKey':value,'CustomerOrderId':row['CustomerOrderId'],'PartId':1,
            'IsSpike':True,'IsElephant':False,'OriginalQty':row['Qty'],'Qty':row['Qty'],
            'SKUCode':row['SKUCode'],'WhCode':row['WhCode'],
            'CustomerExpectedDate':row['CustomerExpectedDate'],
            'FirstServicingWhCode':row['FirstServicingWhCode'],'DueDate':row['DueDate'],'IntroDate':today})
    counter += len(resolved)
    s['OrderIdentity'] = [{'Seed': 1, 'Increment': 1, 'LastValue': counter}]
    yield 'CalculateDD.sql', snapshot(s)
