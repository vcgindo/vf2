"""Deployed BPR async read model, not a second planning calculation.

Source: BPRProcessor in deployed DLL 0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346.
Decompilation: 68b9680373d7edf530fe5985f89d88d67b6fc4f7f1870112230cba9c7bb6b03b.
The grid pages a joined KEY BAG, then rejoins it. Count uses a different join.
Ancillary populations must be supplied explicitly; missing is not empty.
"""
from collections import Counter
from decimal import Decimal
from itertools import product

from mta.presentation.rrr import index, sql_key
from mta.runtime.relational_state import CATALOG, db_value


def native(rows, table):
    columns = dict(CATALOG['tables'][table])
    return [{name: db_value(value, columns[name]) for name, value in row.items()} for row in rows]


def latest_remarks(rows):
    result = {}
    for key, matches in index(rows, 'SKUCode', 'WhCode').items():
        dates = [r['RemarkDate'] for r in matches if r['RemarkDate'] is not None]
        # MAX ignores NULL; equality to NULL does not match any row.
        result[key] = [r for r in matches if dates and r['RemarkDate'] == max(dates)]
    return result


def sort_rows(rows, *, projected=False):
    """SQL NULL ordering and only the declared ORDER BY fields; no tie-break."""
    def value(row, field):
        v = row.get(field)
        if isinstance(v, str):
            v = sql_key(v)[0]
        return (v is not None, v)
    fields = [('PhysicalInventoryColorSequence',False),
              ('TechPen' if projected else '_physical_pen',True), ('es',False),
              ('EcoPen' if projected else '_dispatch_pen',True), ('WHCode',True), ('SKUCode',False)]
    for field, descending in reversed(fields):
        rows = sorted(rows, key=lambda row: value(row,field), reverse=descending)
    return rows


class ReadModel:
    def __init__(self, output, ancillary):
        # These are required consumer inputs, not optional fallback fixtures.
        self.transit = index(ancillary['InTransitData'], 'SKUCode', 'WhCode')
        self.remarks = latest_remarks(ancillary['BPRReport_RemarkDetails'])
        closing = output['ClosingState'][0]
        importer = closing['importer']
        self.base = native(output['BPRReports'][0]['BPR_Table'], 'BPR/BPR_Table')
        self.ration = index(native(output['BPRReports'][0]['vf_RationedReqReport'],
                                  'BPR/vf_RationedReqReport'), 'SKUCode','WhCode')
        self.standard = index(closing['dbm']['SKULocStandardAttributes'], 'SKUCode','WhCode')
        self.sku = index(importer['SkuAttributeData'], 'SKUCode')
        self.location = index(importer['LocationAttributeData'], 'WHCode')
        self.pair = index(importer['SkuLocAttributeData'], 'SKUCode','LocCode')
        self.trend = index(output['BTRFinal'][0]['BufferTrendPhysicalInv'], 'SKUCode','WhCode')

    def joined(self, *, count=False, final=False):
        for a in self.base:
            key = sql_key(a['SKUCode'],a['WhCode'])
            standard = self.standard.get(key, [])
            populations = (
                self.ration.get(key,[]) or [{}], standard if count else standard or [{}],
                self.sku.get(sql_key(a['SKUCode']),[]) or [{}],
                self.location.get(sql_key(a['WhCode']),[]) or [{}],
                self.pair.get(key,[]) or [{}],
                (self.remarks.get(key,[]) or [{}]) if count or final else [{}],
                (self.trend.get(key,[]) or [{}]) if final else [{}],
            )
            for vf, standard, sku, location, pair, remark, trend in product(*populations):
                row = dict(tags=standard.get('Tags'))
                row.update({name:a[name] for name in (
                    'SKUCode','SKUName','ParentWhCode','Stock','Norm','GIT',
                    'ResidualSnP','NormReq','BlueReq')})
                row.update(WHCode=a['WhCode'], WHName=a['WhName'],
                    ParentName=a['ParentName'] if a['ParentName'] is not None else '-',
                    ts=a['TechColorSequence'], es=a['EcoColorSequence'],
                    PhysicalInventoryColorSequence=vf.get('PhysicalInventoryColorSequence'),
                    TechPen=self.pen(vf.get('PhysicalInventoryPen')), EcoPen=self.pen(vf.get('DispatchPen')),
                    TechColor=vf.get('PhysicalInventoryColor'), EcoColor=vf.get('DispatchColor'),
                    vn=vf.get('VirtualNorm'), Remark=remark.get('Remark'),
                    _physical_pen=vf.get('PhysicalInventoryPen'), _dispatch_pen=vf.get('DispatchPen'),
                    _key=key, _base_eco=a['EcoColor'], _pair=pair, _standard=standard)
                row.update({name:0 if a[name] is None else a[name]
                            for name in ('Req','RationedQTY','LeftoverParentStock')})
                row['PhaseIn-Out'] = {1:'Phase Out',2:'Phase In'}.get(a['PhaseIn-Out'],'-')
                row.update({f'sl{i}':sku.get(f'SL{i}') for i in range(1,6)})
                row.update({f'll{i}':location.get(f'LL{i}') for i in range(1,6)})
                row.update({f'SKULocAttr{i}':self.dash(a[f'SKULocAttr{i}']) for i in range(1,16)})
                row.update({f'{prefix}{i}':self.dash(source.get(f'c{i}'))
                    for prefix,source in (('SKUAttr',sku),('LocAttr',location)) for i in range(1,16)})
                row.update({name:trend.get(name) for name in (
                    'Availability_01_30','Availability_31_60','Availability_61_90')})
                yield row

    @staticmethod
    def pen(value):
        return None if value == Decimal('-99999999.00') else value

    @staticmethod
    def dash(value):
        return '-' if value is None else value

    def count_rows(self):
        return list(self.joined(count=True))

    def candidates(self):
        """Apply authenticated scope/filters to this bag BEFORE paging."""
        return sort_rows(list(self.joined()))

    def page(self, selected, page, size):
        if page < 1 or size < 1:
            raise ValueError('positive pagination is required by deployed BPR')
        selected_keys = Counter(row['_key'] for row in selected[(page-1)*size:page*size])
        rows = []
        for row in self.joined(final=True):
            multiplicity = selected_keys[row['_key']]
            if not multiplicity:
                continue
            transit = []
            for t in self.transit.get(row['_key'],[]):
                item = {target:t[source] for target,source in (
                    ('lc','OrderNo'),('cd','CreationDate'),('slt','SLT'),('tlt','TLT'),
                    ('ag','Ageing'),('eta','ETA'),('cl','CurrentLocationCode'),('qty','InTransitQty'),
                    ('remarks','Remark'))}
                item['exeecocolor'] = row['_base_eco']
                transit.append(item)
            projected = {k:v for k,v in row.items() if not k.startswith('_')}
            # Kept structured until the source-backed FOR JSON/wire serializer.
            projected['intransit'] = transit
            rows.extend(dict(projected) for _ in range(multiplicity))
        return sort_rows(rows, projected=True)
