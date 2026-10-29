"""Owned whole-quantity Elephant intake and manual due-date transitions.

Accepted identities follow the approved persisted-ordinal production rule.
No quantity split, inferred due date, or replacement servicing rule is used.
"""
from copy import deepcopy
from datetime import date

from mta.domain.order_identity import MAX_KEY, next_keys

FIELDS = ('CustomerOrderID', 'SKUCode', 'WhCode', 'Qty', 'TopmostWhCode',
          'TopmostWhNorm', 'RLTUptoSuppOrPlant', 'IntroDate',
          'CustomerExpectedDate', 'DueDate')
ACTION = 'elephant_due_date'


def identity(row, customer='CustomerOrderID'):
    return tuple(row[f].rstrip(' ').upper() for f in (customer, 'SKUCode', 'WhCode'))


def validate(rows):
    from mta.application.accepted_inputs import accepted
    if accepted():
        return
    if not isinstance(rows, list):
        raise ValueError('Persisted Elephant row list required')
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(FIELDS):
            raise ValueError('Complete typed Elephant fields required')
        for field in ('CustomerOrderID', 'SKUCode', 'WhCode','TopmostWhCode'):
            value = row[field]
            if (not isinstance(value, str) or not value.strip() or not value.isascii()
                    or '\0' in value or len(value.encode('utf-16-le')) > 100):
                raise ValueError('Elephant identity requires NOT NULL nonblank ASCII nvarchar50')
        for field in ('Qty', 'TopmostWhNorm', 'RLTUptoSuppOrPlant'):
            value = row[field]
            if type(value) is not int or not -2**31 <= value <= MAX_KEY:
                raise ValueError('Elephant numeric field requires a NOT NULL signed integer')
        if row['IntroDate'] is None:
            raise ValueError('Elephant introduction date is NOT NULL')
        for field in ('IntroDate', 'CustomerExpectedDate', 'DueDate'):
            if row[field] is not None:
                value = row[field]
                if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                    raise ValueError('Elephant date requires exact ISO date')


def acceptance(rows, existing, attributes, masters, today, counter):
    """All candidates see the same pre-insert MAX PartId, including duplicates."""
    validate(rows)
    parts = {}
    for row in existing:
        k = identity(row, 'CustomerOrderId')
        parts[k] = max(parts.get(k, 0), row['PartId'])
    candidates = []
    for row in rows:
        if row['DueDate'] is None:
            continue
        attr = attributes.get(identity(row)[1:])
        topmost = attr.get('TopmostWhCode') if attr is not None else None
        parent = (masters.get((row['SKUCode'].rstrip(' ').upper(), topmost.rstrip(' ').upper()))
                  if topmost is not None else None)
        if parent is None:
            continue  # The source deletes due-dated rows even after a failed join.
        part = parts.get(identity(row), 0) + 1
        if part > MAX_KEY:
            raise ValueError('Elephant PartId overflow')
        candidates.append(dict(CustomerOrderId=row['CustomerOrderID'], PartId=part,
            IsSpike=True, IsElephant=True, OriginalQty=row['Qty'], Qty=row['Qty'],
            SKUCode=row['SKUCode'], WhCode=row['WhCode'],
            CustomerExpectedDate=row['CustomerExpectedDate'],
            FirstServicingWhCode=parent['ParentWhCode'], DueDate=row['DueDate'], IntroDate=today))
    accepted = [dict(OrderKey=value, **row)
                for row, value in zip(candidates, next_keys(counter, len(candidates)))]
    return accepted, deepcopy([row for row in rows if row['DueDate'] is None])


def refreshed(row, master):
    required = ('TopmostWhCode', 'TopmostWhNorm', 'RLTTillPlantSupplier')
    if any(field not in master for field in required):
        raise ValueError('Elephant intake requires its computed topmost master attributes')
    result = dict(row, TopmostWhCode=master['TopmostWhCode'],
                  TopmostWhNorm=master['TopmostWhNorm'], RLTUptoSuppOrPlant=master['RLTTillPlantSupplier'])
    validate([result])
    return result


def apply_due_dates(state, selected):
    """One joined VALUES-bag update; duplicate targets retain their ordinals."""
    validate(state['ElephantOrders'])
    if not isinstance(selected, list) or not selected:
        raise ValueError('Nonempty Elephant due-date action required')
    assignments = {}
    for row in selected:
        if not isinstance(row, dict) or set(row) != {'OrderID', 'SKUCode', 'WhCode', 'DueDate'}:
            raise ValueError('Elephant action fields are OrderID/SKUCode/WhCode/DueDate')
        for field in ('OrderID', 'SKUCode', 'WhCode'):
            if not isinstance(row[field], str) or not row[field].strip() or not row[field].isascii():
                raise ValueError('Elephant action identity requires nonblank ASCII')
        value = row['DueDate']
        if value is None or (isinstance(value, str) and not value.strip()):
            value = None
        elif not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
            raise ValueError('Elephant action requires an ISO date or NULL')
        k = identity(row, 'OrderID')
        if k in assignments and assignments[k] != value:
            raise ValueError('Conflicting joined Elephant due-date assignments have no defined winner')
        assignments[k] = value
    result = deepcopy(state)
    for row in result['ElephantOrders']:
        k = identity(row)
        if k in assignments:
            row['DueDate'] = assignments[k]
    return result
