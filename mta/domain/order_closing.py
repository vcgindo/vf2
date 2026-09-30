"""ImportSpikeOrders -> CalculateDD closing state, including SQL identity state.

The selected ordinary-order path reuses the accepted import producer. Elephant
actions remain a separate required contract. Unordered generated keys are not
assigned arbitrary modern tie-breaks.
"""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING

from mta.application.r1_order_input import reconcile_order_feed

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
    if state['ElephantOrders']:
        raise ValueError('Elephant state needs its separate workflow contract')
    identity = state['OrderIdentity']
    if (len(identity) != 1 or set(identity[0]) != {'Seed', 'Increment', 'LastValue'}
            or identity[0]['Seed'] != 1 or identity[0]['Increment'] != 1
            or type(identity[0]['LastValue']) is not int
            or not 1 <= identity[0]['LastValue'] < 2147483647):
        raise ValueError('Explicit selected SQL identity counter required')
    counter = identity[0]['LastValue']
    if any(r['OrderKey'] > counter for r in state['SpikeOrderData']):
        raise ValueError('Order identity counter precedes an existing key')
    masters = indexed(state['BPRMaster'], 'WHCode')
    attributes = indexed(state['AdditionalMasterData'])
    dbm = indexed(state['DBMMaster'])
    source = {'opening_date': opening_date, 'opening_identity': 'own-closing-order-state',
              'feed_status': feed_status, 'feed_rows': deepcopy(feed),
              'opening_orders': state['SpikeOrderData'], 'closure_history': state['SpikeOrderClosureHistory']}
    # The accepted import seam only admits its counter with a nonempty opening.
    # This adapter owns the counter independently even after every row is deleted.
    if state['SpikeOrderData']:
        source['identity_last_value'] = counter
    joined = []
    for k, row in masters.items():
        if k not in attributes:
            raise ValueError('Order closing requires its computed additional master')
        joined.append({'SKUCode': row['SKUCode'], 'WhCode': row['WHCode'], 'Norm': row['Norm'],
                       'SpikeThreshold': attributes[k]['SpikeThreshold'],
                       'ElephantOrderCapping': attributes[k]['ElephantOrderCapping']})
    imported = reconcile_order_feed(source, joined, today)
    old_keys = {r['OrderKey'] for r in state['SpikeOrderData']}
    generated = [r for r in imported['orders'] if r['OrderKey'] not in old_keys]
    if len(generated) > 1:
        raise ValueError('Multiple generated non-Spike identities have no source-defined insertion order')
    if generated:
        counter += 1
        generated[0]['OrderKey'] = counter
    s = deepcopy(state)
    s.update(SpikeOrderData=imported['orders'], SpikeOrderClosureHistory=imported['closure_history'],
             NewSpikeOrders=imported['new_spikes'], PSOData=deepcopy(feed),
             LastBatchRunTbl=[{'LastRunDate': today + 'T00:00:00'}],
             IntermediateTables={name: [] for name in state['IntermediateTables']})
    for rows in (s['SpikeOrderData'], s['SpikeOrderClosureHistory']):
        for row in rows:
            row['IsSpike'], row['IsElephant'] = bool(row['IsSpike']), bool(row['IsElephant'])
    s['OrderIdentity'] = [{'Seed': 1, 'Increment': 1, 'LastValue': counter}]
    yield 'ImportSpikeOrders.sql', deepcopy(s)

    # Literal selected SQL level loop: one INSERT SELECT per level. Its anti-join
    # intentionally omits WhCode. All candidates see the pre-insert population.
    pending = []
    max_level = max((r['WhLevel'] for r in attributes.values()), default=-1)
    for level in range(max_level, -1, -1):
        for row in s['NewSpikeOrders']:
            a = attributes.get(key(row['SKUCode'], row['WhCode']))
            if a is not None and a['WhLevel'] == level:
                pending.append({**row, 'CurrentWhCode': row['WhCode'], 'Norm': 0, 'RLT': 0,
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
        existing = {key(r['CustomerOrderId'], r['SKUCode']) for r in s['SpikeOrderData']}
        candidates = [r for r in pending if r['FirstServicingWhCode'] is not None
                      and key(r['CustomerOrderId'], r['SKUCode']) not in existing]
        if len(candidates) > 1:
            raise ValueError('Multiple generated Spike identities share an unordered CalculateDD insertion')
        for row in candidates:
            counter += 1
            if counter > 2147483647:
                raise ValueError('SQL order identity exhausted')
            s['SpikeOrderData'].append({
                'OrderKey': counter, 'CustomerOrderId': row['CustomerOrderId'], 'PartId': 1,
                'IsSpike': True, 'IsElephant': False, 'OriginalQty': row['Qty'], 'Qty': row['Qty'],
                'SKUCode': row['SKUCode'], 'WhCode': row['WhCode'],
                'CustomerExpectedDate': row['CustomerExpectedDate'],
                'FirstServicingWhCode': row['FirstServicingWhCode'], 'DueDate': row['DueDate'], 'IntroDate': today})
        pending = [r for r in pending if r['FirstServicingWhCode'] is None]
        for row in pending:
            parent = dbm.get(key(row['SKUCode'], row['CurrentWhCode']))
            if parent is not None:
                row['CurrentWhCode'] = parent['ParentWhCode']
                row['RLT'] += parent['RLT']
    s['OrderIdentity'] = [{'Seed': 1, 'Increment': 1, 'LastValue': counter}]
    yield 'CalculateDD.sql', deepcopy(s)
