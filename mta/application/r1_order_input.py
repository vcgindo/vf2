"""R1-05 standard order feed/opening boundary, independent of site adapters.

Canonical ImportSpikeOrders.sql owns amendment/closure, not the downstream
allocation engine. This producer stops before CalculateDD for newly classified
spikes. No customer-format transformation or replacement Elephant handler.
"""
from mta.application.stage_observation import summary
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_CEILING
from mta.domain.order_identity import counter as identity_counter, next_keys

FEED_FIELDS = ('OrderID', 'SKUCode', 'WhCode', 'Qty', 'CustomerExpDate')
ORDER_FIELDS = ('OrderKey', 'CustomerOrderId', 'PartId', 'IsSpike', 'IsElephant',
                'OriginalQty', 'Qty', 'SKUCode', 'WhCode', 'CustomerExpectedDate',
                'FirstServicingWhCode', 'DueDate', 'IntroDate')
CLOSURE_FIELDS = tuple(f for f in ORDER_FIELDS if f not in ('OrderKey', 'PartId')) + ('ClosureDate',)


def _key(row, field='CustomerOrderId'):
    # Selected ASCII SQL key contract; wider collation remains unverified.
    return tuple(row[f].rstrip(' ').upper() for f in (field, 'SKUCode', 'WhCode'))


def validate_order_input(source, business_date):
    if not isinstance(source, dict) or set(source) - {'sku_attributes', 'identity_last_value'} != {
        'opening_date', 'opening_identity', 'feed_status', 'feed_rows', 'opening_orders', 'closure_history',
    }:
        raise ValueError('Explicit standard order feed and prior-state contract required')
    if 'sku_attributes' in source:
        attributes = source['sku_attributes']
        if not isinstance(attributes, list):
            raise ValueError('Order SKU attributes must be source rows')
        seen = set()
        for row in attributes:
            if not isinstance(row, dict) or set(row) != {'SKUCode','ElephantOrderCapping'}:
                raise ValueError('Invalid order SKU attribute fields')
            sku, cap = row['SKUCode'], row['ElephantOrderCapping']
            if not isinstance(sku, str) or not sku.strip() or sku in seen:
                raise ValueError('Order SKU attributes require unique nonblank SKU')
            if cap is not None and (type(cap) is not int or not 0 <= cap <= 2147483647):
                raise ValueError('Order Elephant cap must be nullable nonnegative SQL integer')
            seen.add(sku)
    if date.fromisoformat(source['opening_date']) >= date.fromisoformat(business_date):
        raise ValueError('Order opening must precede business date')
    if not isinstance(source['opening_identity'], str) or not source['opening_identity'].strip():
        raise ValueError('Labelled synthetic prior order identity required')
    if source['feed_status'] not in ('PRESENT', 'MISSING'):
        raise ValueError('Order feed availability must be explicit')
    if source['feed_status'] == 'MISSING' and source['feed_rows']:
        raise ValueError('Missing order feed cannot contain rows')
    for name, fields in (('feed_rows', FEED_FIELDS), ('opening_orders', ORDER_FIELDS),
                         ('closure_history', CLOSURE_FIELDS)):
        if not isinstance(source[name], list):
            raise ValueError('Order source tables must be row lists')
        for row in source[name]:
            if not isinstance(row, dict) or set(row) != set(fields):
                raise ValueError('Invalid standard order source fields: ' + name)
            for field in ('SKUCode', 'WhCode', 'OrderID' if name == 'feed_rows' else 'CustomerOrderId'):
                if not isinstance(row[field], str) or not row[field].strip() or not row[field].isascii():
                    raise ValueError('Selected order identity requires nonblank ASCII')
            for field in ('Qty', 'OriginalQty', 'OrderKey', 'PartId'):
                if field in row and (type(row[field]) is not int or not 0 <= row[field] <= 2147483647):
                    raise ValueError('Order quantity/key must be a nonnegative SQL integer')
            for field in ('IsSpike', 'IsElephant'):
                if field in row and row[field] not in (0, 1):
                    raise ValueError('Order classification must be 0 or 1')
            for field in ('CustomerExpDate', 'CustomerExpectedDate', 'DueDate', 'IntroDate', 'ClosureDate'):
                if field in row and row[field] is not None:
                    date.fromisoformat(row[field])
            if 'IntroDate' in row and (row['IntroDate'] is None or row['IntroDate'] > source['opening_date']):
                raise ValueError('Opening order introduction must not be from current/future day')
    keys = [r['OrderKey'] for r in source['opening_orders']]
    if len(keys) != len(set(keys)):
        raise ValueError('Opening OrderKey must be unique')
    if 'identity_last_value' in source:
        counter = source['identity_last_value']
        identity_counter(counter)
        if keys and counter < max(keys):
            raise ValueError('Selected identity counter must cover historical orders')
    feed_keys = [_key(r, 'OrderID') for r in source['feed_rows']]
    if len(feed_keys) != len(set(feed_keys)):
        raise ValueError('Duplicate feed UPDATE winner is unverified; no arbitrary selection')


def reconcile_order_feed(source, master_rows, business_date, *, accepted_orders=(), elephant_orders=None):
    """master_rows: SKUCode/WhCode/Norm/SpikeThreshold/ElephantOrderCapping.

    Returns retained/amended orders, newly classified orders and full closure
    history. New non-Spikes use the explicit owned counter in preserved feed
    order under the approved production contract, not canonical insertion parity.
    Without that counter, OrderKey=None remains unverified.
    Existing per-part identity is retained. Legacy applies feed Qty to EACH
    existing part; this function deliberately does not invent a split rule.
    """
    validate_order_input(source, business_date)
    masters = {}
    for row in master_rows:
        key = _key(dict(row, CustomerOrderId=''))[1:]
        if key in masters:
            raise ValueError('Duplicate master order join requires discrimination')
        masters[key] = row
    orders = deepcopy(source['opening_orders']) + deepcopy(list(accepted_orders))
    elephants = None
    if elephant_orders is not None:
        from mta.domain.elephant_orders import validate, refreshed, identity
        validate(elephant_orders)
        elephants = deepcopy(elephant_orders)
    history = deepcopy(source['closure_history'])
    feed = [deepcopy(r) for r in source['feed_rows'] if _key(r, 'OrderID')[1:] in masters]
    # The source tests raw PSOData emptiness BEFORE filtering to master.
    raw_empty = not source['feed_rows']
    current_keys = {_key(r, 'OrderID') for r in feed}
    if elephants is not None:
        elephants = [r for r in elephants if (identity(r)[1:] in masters if raw_empty
                                              else identity(r) in current_keys)]
    retained = []
    for row in orders:
        close = _key(row)[1:] not in masters if raw_empty else _key(row) not in current_keys
        if close:
            history.append({**{f: row[f] for f in CLOSURE_FIELDS if f != 'ClosureDate'},
                            'ClosureDate': business_date})
        else:
            retained.append(row)
    if raw_empty:
        result = dict(orders=retained, new_spikes=[], closure_history=history,
                      feed_status=source['feed_status'], outcome='EMPTY_FEED_RETAINED')
        if elephants is not None: result['elephant_orders'] = elephants
        return result
    new_spikes = []
    retained_by_key = {}
    for ordinal, row in enumerate(retained):
        retained_by_key.setdefault(_key(row), []).append((ordinal, row))
    removed = set()
    elephant_by_key = {}
    if elephants is not None:
        for ordinal, row in enumerate(elephants):
            elephant_by_key.setdefault(identity(row), []).append((ordinal, row))
    removed_elephants = set()
    matched_rows = 0
    for incoming in feed:
        key = _key(incoming, 'OrderID')
        master = masters[key[1:]]
        threshold = (Decimal(str(master['Norm'])) * Decimal(str(master['SpikeThreshold'])) / 100
                     ).to_integral_value(rounding=ROUND_CEILING)
        bucket = retained_by_key.get(key, [])
        matched_rows += len(bucket) + len(elephant_by_key.get(key, ()))
        spike = any(r['IsSpike'] == 1 for _, r in bucket) or incoming['Qty'] > threshold
        if elephants is not None:
            changed = []
            for ordinal, row in elephant_by_key.get(key, ()):
                row = refreshed(row, master)
                row['Qty'] = incoming['Qty']
                if row['Qty'] <= (0 if master['ElephantOrderCapping'] is None else master['ElephantOrderCapping']):
                    removed_elephants.add(ordinal)
                    continue
                elephants[ordinal] = row
                changed.append((ordinal, row))
            elephant_by_key[key] = changed
        # Canonical removes promoted PSOs before matching existing orders.
        if spike:
            kept = []
            for ordinal, row in bucket:
                if row['IsSpike'] == 0:
                    removed.add(ordinal)
                else:
                    kept.append((ordinal, row))
            bucket = kept
            retained_by_key[key] = bucket
        matches = [row for _, row in bucket]
        for row in matches:
            row['Qty'] = incoming['Qty']  # no amendment to OriginalQty/CED/DD
        if matches:
            continue
        if 'ElephantOrderCapping' not in master:
            raise ValueError('R1-05 new order needs source-owned Elephant cap; no assumed default')
        cap = master['ElephantOrderCapping']
        if incoming['Qty'] > (0 if cap is None else cap):
            if elephants is None:
                raise ValueError('R1-05 Elephant source path requires its connected owner')
            if not elephant_by_key.get(key):
                elephants.append(refreshed(dict(CustomerOrderID=incoming['OrderID'],
                    SKUCode=incoming['SKUCode'], WhCode=incoming['WhCode'], Qty=incoming['Qty'],
                    IntroDate=business_date, CustomerExpectedDate=incoming['CustomerExpDate'], DueDate=None), master))
                elephant_by_key.setdefault(key, []).append((len(elephants)-1, elephants[-1]))
        if elephants is not None and elephant_by_key.get(key):
            continue
        if spike:
            new_spikes.append(dict(CustomerOrderId=incoming['OrderID'], SKUCode=incoming['SKUCode'],
                                   WhCode=incoming['WhCode'], Qty=incoming['Qty'],
                                   CustomerExpectedDate=incoming['CustomerExpDate']))
        else:
            retained.append(dict(OrderKey=None, CustomerOrderId=incoming['OrderID'], PartId=1,
                                 IsSpike=0, IsElephant=0, OriginalQty=incoming['Qty'], Qty=incoming['Qty'],
                                 SKUCode=incoming['SKUCode'], WhCode=incoming['WhCode'],
                                 CustomerExpectedDate=incoming['CustomerExpDate'], FirstServicingWhCode=None,
                                 DueDate=None, IntroDate=business_date))
            retained_by_key.setdefault(key, []).append((len(retained)-1, retained[-1]))
    summary('r1_order_feed_indexes', index_builds=1 + (elephants is not None),
            indexed_rows=len(orders) + (len(elephants) if elephants is not None else 0),
            lookup_probes=len(feed), matched_rows=matched_rows)
    retained = [row for ordinal, row in enumerate(retained) if ordinal not in removed]
    if elephants is not None:
        elephants = [row for ordinal, row in enumerate(elephants) if ordinal not in removed_elephants]
    generated = [r for r in retained if r['OrderKey'] is None]
    if generated and 'identity_last_value' in source:
        # Filtering/classification above preserves supplied ordinals. Ordinary
        # rows are assigned before the separately resolved Spike subset.
        for row, value in zip(generated, next_keys(source['identity_last_value'], len(generated))):
            row['OrderKey'] = value
    result = dict(orders=retained, new_spikes=new_spikes, closure_history=history,
                  feed_status=source['feed_status'], outcome='APPLIED')
    if elephants is not None: result['elephant_orders'] = elephants
    return result
