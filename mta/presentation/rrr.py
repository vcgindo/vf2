"""Selected deployed RRR SELECT over already-calculated relational facts.

Producer SQL: GenerateBifurcationOfRationedReq.sql SHA256
8da7fde0a88fd29a8c1f3af0d92ff578be50262f1b5605be8421a1686c45f0b5.
Deployed RRRProcessor decompilation SHA256
d59a23788cb992f0413fb39fe43744043acea57804432d4eda8e09a1ac8dda82
(assembly0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346).
No requirement/ration/band calculation belongs in this adapter.
"""
from collections import defaultdict
from decimal import Decimal
from itertools import product

from mta.runtime.relational_state import CATALOG


def sql_key(*values):
    if any(v is None for v in values):
        return None
    return tuple(str(v).rstrip(' ').casefold() for v in values)


def index(rows, *fields):
    result = defaultdict(list)
    for row in rows:
        key = sql_key(*(row[f] for f in fields))
        if key is not None:
            result[key].append(row)
    return result


def pick_rows(rationed, bands):
    """Copy the two source report populations; take bands only from producer.

The accepted native rationed-report constructor has one row per SKU/location.
Do not silently select a duplicate or multiply an already materialized band.
Band ordinals (including duplicate bands) are retained without deduplication.
"""
    positions = index(rationed, 'SKUCode', 'WhCode')
    columns = CATALOG['tables']['BPR/vf_RationedReqReport']
    decimals = {name for name, kind in columns if kind in ('decimal', 'numeric')}
    result = []
    for band in bands:
        key = sql_key(band['sku_code'], band['location_code'])
        parents = positions.get(key, [])
        if len(parents) != 1:
            raise ValueError('Pick band requires its unique produced rationed-report position')
        row = dict(parents[0])
        for name in decimals:
            if row[name] is not None:
                row[name] = Decimal(str(row[name]))
        if sql_key(band['location_code']) == sql_key(band['parent_location_code']):
            # Exact virtual-node INSERT aliases/literals; not new allocation.
            row.update(ParentWhCode=row['WhCode'], ParentWhName=row['WhName'], ParentNorm=row['Norm'],
                TechPenParent=row['TechPen'], TechColorParent=row['TechColor'],
                EcoPenParent=row['EcoPen'], EcoColorParent=row['EcoColor'],
                Req=0, AllocatedForVirtualNormReq=0, AllocatedForNormReq=0,
                AllocatedForSnPReq=0, RationedReq=0, RationedCasePacks=0,
                LeftoverParentStock=row['LeftoverStock'], LeftoverStock=0,
                ParentPackSize=row['PackSize'], IsNormed=False, SpikeOverdueAtParent=0,
                ResidualChildrenSnP=0, AvgSiblingsNorm=row['AvgChildrenNorm'], AvgChildrenNorm=0,
                ParentStockPercentageForRationing=row['StockPercentageForRationing'],
                ParentNormPercentReservation=row['NormPercentReservation'])
        elif sql_key(row['ParentWhCode']) == sql_key(band['parent_location_code']):
            row['AllocatedForDirectOrders'] = 0
        else:
            raise ValueError('Pick band parent differs from produced report')
        row.update({target: int(band[source]) for target, source in (
            ('TOR_B','to_black'),('TOR_R','to_red'),('TOY','to_yellow'),('TOG','to_green'),('TOBlue','to_blue'))})
        result.append(row)
    return result


ALIASES = dict(TPen='PhysicalInventoryPen', TCol='PhysicalInventoryColor',
    EPen='DispatchPen', ECol='DispatchColor', PWh='ParentWhCode', PWhName='ParentWhName',
    TPenParent='TechPenParent', TColParent='TechColorParent',
    EPenParent='EcoPenParent', EColParent='EcoColorParent', RReq='RationedReq',
    torb='TOR_B', torr='TOR_R', toy='TOY', tog='TOG', tob='TOBlue',
    RCPs='RationedCasePacks', LPS='LeftoverParentStock', ParentPacksize='ParentPackSize',
    ParentNormPercentageReservation='ParentNormPercentReservation')
DIRECT_FIELDS = '''DispatchColorSequence SKUCode SKUName WhCode WhName Norm VirtualNorm
VirtualNodeNorm SpikeThreshold PSOThreshold Stock GIT StockForRationing StockForReqCalc
DispatchPen DispatchColor ParentNorm Req AllocatedForVirtualNormReq AllocatedForNormReq
AllocatedForSnPReq AllocatedForDirectOrders PackSize LeftoverStock IsNormed DirectSpikeOverdue
SpikeOverdueAtParent PSO RelPSOAndCNR ResidualChildrenSnP SnPToNetOff SnPNettedOff ResidualSnP
EcoStockForNormReq NormReq BlueReq AvgSiblingsNorm AvgChildrenNorm ParentStockForNormRationing
ParentStockForSnPRationing ParentStockForRationing StockPercentageForRationing
NormPercentReservation ParentStockPercentageForRationing'''.split()
NULL_DASH = ('SKUName','WhName','TCol','ECol','PWhName','TColParent','EColParent')


def selected_rows(output, bands, *, predicate=None):
    """SQL inner/left joins, preserving every attribute-join multiplicity."""
    closing = output['ClosingState'][0]
    importer = closing['importer']
    standard = index(closing['dbm']['SKULocStandardAttributes'], 'SKUCode', 'WhCode')
    sku = index(importer['SkuAttributeData'], 'SKUCode')
    location = index(importer['LocationAttributeData'], 'WHCode')
    pair = index(importer['SkuLocAttributeData'], 'SKUCode', 'LocCode')
    result = []
    for source in pick_rows(output['BPRReports'][0]['vf_RationedReqReport'], bands):
        key = sql_key(source['SKUCode'], source['WhCode'])
        # B and sla are two distinct selected joins to SkuLocAttributeData.
        # The latter is LEFT, but the earlier inner B guarantees a matching bag.
        for _, b, c, d, _sla in product(standard.get(key, []), pair.get(key, []),
                sku.get(sql_key(source['SKUCode']), []),
                location.get(sql_key(source['WhCode']), []), pair.get(key, [])):
            multiplicity = predicate(source,b,c,d) if predicate is not None else 1
            if not multiplicity:
                continue
            row = {name: source[name] for name in DIRECT_FIELDS}
            row.update({name: source[column] for name, column in ALIASES.items()})
            for name in NULL_DASH:
                if row[name] is None:
                    row[name] = '-'
            if row['ParentNorm'] is None:
                # Selected ISNULL(int ParentNorm,'-') is a conversion failure,
                # not authorization to synthesize a parent Norm or suppress it.
                raise ValueError('Canonical RRR ParentNorm NULL conversion is not comparable')
            row.update({f'sl{i}': c[f'SL{i}'] for i in range(1,6)})
            row.update({f'll{i}': d[f'LL{i}'] for i in range(1,6)})
            row.update({f'{prefix}{i}': '-' if values[f'c{i}'] is None else values[f'c{i}']
                for prefix, values in (('SKULocAttr',b),('SKUAttr',c),('LocAttr',d)) for i in range(1,16)})
            result.extend(dict(row) for _ in range(multiplicity))
    # No added tie-break. Selected SQL does not order tied rows further.
    return sorted(result, key=lambda r: (r['DispatchColorSequence'], -r['DispatchPen'],
                                        sql_key(r['WhCode']), sql_key(r['SKUCode'])))
