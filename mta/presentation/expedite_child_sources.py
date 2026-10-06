"""Native child-Expedite scalar request and nested shipment projections.

PlanningProcessor SHA bf716c4f84e43920b5f2ab302e3d3c78ec685f5d714471c53047d377537d3486,
ExpediteFromChild: request TOP(1) by RequestDate descending; shipment pair match
with FOR JSON PATH, INCLUDE_NULL_VALUES. No parent condition on shipments.
"""
from datetime import datetime
import json
from mta.presentation.rrr import index, sql_key
from mta.serialization import storage

TRANSIT_ALIASES = dict(lc='OrderNo', cd='CreationDate', slt='SLT', tlt='TLT',
                      ag='Ageing', eta='ETA', cl='CurrentLocationCode',
                      qty='InTransitQty', remarks='Remark')


def projections(requests, transit):
    latest = {}
    for key, rows in index(requests, 'SKUCode', 'WhCode', 'ParentWhCode').items():
        dated = [(datetime.fromisoformat(row['RequestDate'])
                  if row['RequestDate'] is not None else datetime.min, row) for row in rows]
        stamp = max(value for value, _ in dated)
        values = {row['Request'] for value, row in dated if value == stamp}
        if len(values) != 1:
            raise ValueError('child_expedite_ambiguous_latest_request')
        latest[key] = values.pop()
    nested = {key: json.dumps(storage([{alias: row[field] for alias, field in TRANSIT_ALIASES.items()}
                                      for row in rows]), separators=(',', ':'), ensure_ascii=False).replace('/', '\\/')
              for key, rows in index(transit, 'SKUCode', 'WhCode').items()}

    def lookup(sku, location, parent):
        return dict(remark=latest.get(sql_key(sku, location, parent)),
                    intransit=nested.get(sql_key(sku, location), '[]'))
    return lookup
