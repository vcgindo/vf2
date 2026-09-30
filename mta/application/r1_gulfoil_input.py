"""GulfOil R1-02 file landing and site import, from the selected deployed SQL.

Source: deployed-demo/MTA/V6/Scripts/SiteSpecific/GulfOil/Importer/
ImportRawDailyData.sql (SHA256 6bb107f1...) and ImportPSOData.sql
(SHA256 d688b3bb...). This module consumes source facts, never SQL results.
Ambiguous UPDATE FROM winners and BOM FIRST_VALUE peers are reported, not chosen.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from copy import deepcopy
import hashlib


LANDING_TABLES = frozenset({
    'BOM_Detail', 'Consumption_ReceiptFile', 'LocationStorageMapping',
    'In_Transit_Stok', 'Indent_Report', 'OPEN_SALES_ORDER', 'Plant_Wip',
    'STOCK_ON_HAND',
})
GULFOIL_PROFILE = 'GulfOil'
FILE_SCHEMA = 'r1-gulfoil-file-input-v1'


def prepare_gulfoil_standard_input(bundle):
    """Files -> site producers -> existing v8 source entry, with owned lineage.

    No producer output may be supplied in the two feed slots. Other standard
    facts and historical openings remain independently declared by the caller.
    """
    from mta.application.r1_file_input import map_csv_inputs
    from mta.application.r1_input import R1EntryFailure
    if bundle.get('schema') != FILE_SCHEMA:
        raise ValueError('Unsupported GulfOil file input schema')
    _require_profile(bundle.get('profile'))
    standard = deepcopy(bundle['standard_input'])
    if standard['schema'] != 'r1-current-day-input-v8':
        raise ValueError('GulfOil connection requires v8 standard input')
    if standard['raw_daily_entry']['raw_daily_data'] or standard['order_input']['feed_rows']:
        raise ValueError('GulfOil file producers own daily and PSO feed slots')
    if any(r['Parameter']=='NMSActive' and str(r['Value'])!='0'
           for r in standard['raw_master_entry']['settings']):
        raise ValueError('Active GulfOil NMS snapshot connection is not certified')
    files=[]
    for row in bundle['files']:
        content=row['text'].encode(row['encoding'])
        if hashlib.sha256(content).hexdigest()!=row['sha256']:
            raise ValueError('GulfOil file checksum mismatch: '+row['name'])
        files.append(dict(name=row['name'],content=content,encoding=row['encoding']))
    entry=standard['raw_master_entry']
    parsed=map_csv_inputs(bundle['mapping'],files,entry['business_date'])
    if parsed['status']!='VALIDATED':
        raise R1EntryFailure('GulfOil file parsing failed',stage='gulfoil_file_input',evidence=parsed)
    landing=map_landing_rows(parsed['tables'],bundle['interface_columns'],profile='GulfOil')
    prior=gulfoil_prior(standard,bundle['adapter_prior'])
    transformed=transform_gulfoil(landing,prior,entry['business_date'],entry['run_timestamp'],bundle['qty2_days'],profile='GulfOil')
    if transformed['status']!='SOURCE_KNOWN':
        raise R1EntryFailure('GulfOil ambiguous source transform',stage='gulfoil_transform',evidence=transformed)
    standard=connect_gulfoil_outputs(standard,transformed)
    return standard,dict(source=bundle,landing=landing,parser=parsed,transformation=transformed)


def gulfoil_prior(standard, adapter_prior):
    entry=standard['raw_master_entry']
    owned={'MasterDataRaw':entry['raw_master'],'MasterData':entry['prior']['MasterData'],
           'MasterDataRawNonNMS':entry['raw_non_nms'],
           'SkuLocAttributeData':entry['prior']['SkuLocAttributeData']}
    if set(owned)&set(adapter_prior):
        raise ValueError('Adapter prior cannot override standard master facts')
    return {**deepcopy(adapter_prior),**deepcopy(owned)}


def connect_gulfoil_outputs(standard, transformed):
    """Structural field map shared with the oracle, never a calculation."""
    result=deepcopy(standard)
    def integer(value):
        if value is None:return None
        number=Decimal(str(value))
        if number!=number.to_integral_value():raise ValueError('Nonintegral daily/PSO output')
        return int(number)
    result['raw_daily_entry']['raw_daily_data']=[{
        **{k:r[k] for k in ('SKUCode','WhCode')},
        **{k:integer(r[k]) for k in ('Stock','Consumption','GIT','Receipts','PSO')},
        'ReportDate':str(r['ReportDate'])[:10]} for r in transformed['DailyDataRaw']]
    result['order_input']['feed_rows']=[dict(OrderID=_v(r,'OrderId'),SKUCode=r['SKUCode'],WhCode=r['WhCode'],
        Qty=integer(r['Qty']),CustomerExpDate=None if r['Extra'] is None else str(r['Extra'])[:10]) for r in transformed['PSOData']]
    result['raw_master_entry']['raw_master']=deepcopy(transformed['MasterDataRaw'])
    result['raw_master_entry']['prior']['SkuLocAttributeData']=deepcopy(transformed['SkuLocAttributeData'])
    # Site rejection rows precede normal validation; preserve their provenance.
    result['raw_master_entry']['prior']['RejectedMaster'].extend(deepcopy(transformed['RejectedMaster']))
    return result


def _require_profile(profile):
    if profile != GULFOIL_PROFILE:
        raise ValueError('GulfOil selected profile required')


def convert_non_nms(attributes, *, profile):
    """Selected NormChangesRun site hook, after validation/norm processing.

    ConvertNonNMSItemsToNMS.sql updates every NonNMS=1, including zero Norm.
    This is separate from daily import and is never a common-engine default.
    """
    _require_profile(profile)
    result = [dict(row) for row in attributes]
    for row in result:
        if _v(row, 'NonNMS') == 1:
            _set(row, 'NonNMS', 0)
    return result


def map_landing_rows(tables, interface_columns, *, profile):
    """Map r1_file_input positional strings to selected Interface column names.

    ``interface_columns`` is readiness-metadata.json's interface_columns list.
    The selected landing columns are all nullable nvarchar; an empty parsed
    string stays empty (SQL NULL is accepted only when supplied explicitly).
    """
    _require_profile(profile)
    schemas = defaultdict(list)
    for column in interface_columns:
        if column['table_name'] in LANDING_TABLES:
            if column['type_name'].lower() != 'nvarchar':
                raise ValueError('selected landing schema is not nvarchar')
            schemas[column['table_name']].append(column)
    mapped = {}
    for table in LANDING_TABLES:
        columns = [c['column_name'] for c in sorted(schemas[table], key=lambda c: c['column_id'])]
        if not columns:
            raise ValueError(f'missing selected interface schema: {table}')
        mapped[table] = []
        for values in tables.get(table, []):
            if len(values) != len(columns):
                raise ValueError(f'{table}: expected {len(columns)} values, got {len(values)}')
            mapped[table].append(dict(zip(columns, values)))
    return mapped


def _v(row, key):
    for name, value in row.items():
        if name.lower() == key.lower():
            return value
    return None


def _set(row, key, value):
    for name in row:
        if name.lower() == key.lower():
            row[name] = value
            return
    row[key] = value


def _eq(a, b):
    return a is not None and b is not None and str(a).rstrip().casefold() == str(b).rstrip().casefold()


def _has(value, needle):
    return value is not None and needle.casefold() in str(value).casefold()


def _trim(value, commas=False):
    return None if value is None else str(value).replace(',', '') .strip() if commas else str(value).strip()


def _leading_zero(value):
    return None if value is None else str(value).replace('0', ' ').lstrip().replace(' ', '0')


def _split(value):
    if value is None:
        return None, ''
    value = str(value)
    parts = value.split('_', 1)
    return parts[0], parts[1] if len(parts) == 2 else ''


def _decimal(value, scale=3, tolerant=False):
    if value is None:
        return Decimal(0) if tolerant else None
    if str(value).strip() == '':
        return Decimal(0)
    try:
        number = Decimal(str(value).strip())
        if not number.is_finite():
            raise InvalidOperation
        return number.quantize(Decimal(1).scaleb(-scale), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        if tolerant:
            return Decimal(0)
        raise ValueError(f'legacy decimal conversion failed: {value!r}')


def _round(value, scale=0):
    return None if value is None else value.quantize(Decimal(1).scaleb(-scale), rounding=ROUND_HALF_UP)


def _date105(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        raise ValueError('legacy date conversion failed: NULL')
    try:
        return datetime.strptime(str(value).strip(), '%d-%m-%Y').date()
    except ValueError as error:
        raise ValueError(f'legacy date conversion failed: {value!r}') from error


def _rows(prior, name):
    return [dict(row) for row in prior.get(name, [])]


def _key(row, loc='WhCode'):
    return (_v(row, 'SKUCode'), _v(row, loc))


def transform_gulfoil(landing, prior, business_date, run_datetime, qty2_days, *, profile):
    """Return selected import outputs plus changed interface/master side effects.

    ``landing`` is map_landing_rows output. ``prior`` holds independent rows
    for MasterDataRaw, MasterData, MasterDataRawNonNMS,
    SkuLocAttributeData, SKULocStandardAttributes, SKUMappedLocations,
    Indent_Report_LocationType, SKULocPriceSLTMaster,
    SKULocUOMMasterTable, and BORWithOrderAllocation. Values may be SQL NULL.
    A result with status AMBIGUOUS is incomparable for the listed branches.
    """
    _require_profile(profile)
    today = date.fromisoformat(business_date) if isinstance(business_date, str) else business_date
    raw = _rows(prior, 'MasterDataRaw')
    master = _rows(prior, 'MasterData')
    nonnms = _rows(prior, 'MasterDataRawNonNMS')
    attrs = _rows(prior, 'SkuLocAttributeData')
    standards = _rows(prior, 'SKULocStandardAttributes')
    mapped_wh = _rows(prior, 'SKUMappedLocations')
    indent_types = _rows(prior, 'Indent_Report_LocationType')
    price = _rows(prior, 'SKULocPriceSLTMaster')
    uom = _rows(prior, 'SKULocUOMMasterTable')
    bor = _rows(prior, 'BORWithOrderAllocation')
    files = {name: [dict(row) for row in landing.get(name, [])] for name in LANDING_TABLES}
    ambiguity = []
    rejections = []

    def reject(row, code, description, sku='SKUCode', wh='WhCode'):
        rejections.append(dict(SKUCode=_v(row, sku) if _v(row, sku) is not None else '-',
                               WhCode=_v(row, wh) if _v(row, wh) is not None else '-',
                               RejectionDate=run_datetime, ReasonCode=code,
                               ReasonDescription=description))

    # Full outer joins preserve duplicate multiplicity. A lone unmatched row
    # appears once; matching duplicates form a Cartesian product.
    def full_keys(left, right):
        result = []
        matched = set()
        for a in left:
            hits = [(i, b) for i, b in enumerate(right) if _eq(_v(a, 'SKUCode'), _v(b, 'SKUCode')) and _eq(_v(a, 'WhCode'), _v(b, 'WhCode'))]
            if hits:
                result.extend((_v(a, 'SKUCode'), _v(a, 'WhCode')) for _ in hits)
                matched.update(i for i, _ in hits)
            else:
                result.append(_key(a))
        result.extend(_key(b) for i, b in enumerate(right) if i not in matched)
        return result

    first = [dict(SKUCode=s, WhCode=w) for s, w in full_keys(raw, master)]
    daily = [dict(SKUCode=s, WhCode=w, Stock=None, Consumption=None, GIT=None,
                  Receipts=Decimal(0), PSO=None)
             for s, w in full_keys(first, nonnms) if s is not None and w is not None]

    for row in raw:
        for field in ('SKULocAtt03', 'SKULocAtt06', 'SKULocAtt09', 'SKULocAtt10', 'SKULocAtt12', 'SKULocAtt13', 'SKULocAtt14'):
            _set(row, field, None)
    for row in attrs:
        for field in ('c3', 'c6', 'c9', 'c10', 'c12', 'c13', 'c14'):
            _set(row, field, None)

    old = list({(_v(a, 'SKUCode'), _v(a, 'SKUAtt04'), _v(a, 'WhCode'))
                for a in raw for b in mapped_wh if _eq(_v(a, 'WhCode'), _v(b, 'WhCode'))
                and _v(a, 'SKUAtt04') not in (None, '')})
    def old_map(sku, wh, reverse=False):
        hits = [s if reverse else c4 for s, c4, w in old
                if _eq(c4 if reverse else s, sku) and _eq(w, wh)]
        if len({str(x).casefold() for x in hits}) > 1:
            ambiguity.append(f'GulfOil_OldSKUMaster UPDATE/joins: {sku}/{wh}')
        return hits or [sku]

    mapping = files['LocationStorageMapping']
    for row in mapping:
        for field in ('VectorLocation', 'LocCode', 'LocDesc', 'StorageLoc', 'DaystobeConsidered'):
            _set(row, field, _trim(_v(row, field)))
        for field in ('UnrestrictedStock', 'BlockedStock', 'QualityStock', 'ReservedStock'):
            _set(row, field, _trim(_v(row, field), commas=True))
    mapping[:] = [r for r in mapping if not _has(_v(r, 'VectorLocation'), 'VectorLocation')
                  and not any(str(_v(r, f)).endswith('-') for f in ('UnrestrictedStock', 'BlockedStock', 'QualityStock', 'ReservedStock') if _v(r, f) is not None)]
    any_pairs = {(_v(r, 'VectorLocation'), _v(r, 'LocCode')) for r in mapping if _eq(_v(r, 'StorageLoc'), 'Any')}
    mapping[:] = [r for r in mapping if _eq(_v(r, 'StorageLoc'), 'Any') or
                  not any(_eq(_v(r, 'VectorLocation'), v) and _eq(_v(r, 'LocCode'), l) for v, l in any_pairs)]

    def mappings(wh):
        loc, storage = _split(wh)
        return [m for m in mapping if _eq(_v(m, 'LocCode'), loc) and
                (_eq(_v(m, 'StorageLoc'), 'Any') or _eq(_v(m, 'StorageLoc'), storage))]

    def missing_storage(rows, file, sku='SKUCode', wh='WhCode', split=True):
        for r in rows:
            location = _v(r, wh)
            loc, storage = _split(location) if split else (location, '')
            if storage == '' and not any(_eq(_v(m, 'LocCode'), loc) and
                    (_eq(_v(m, 'StorageLoc'), 'Any') or _eq(_v(m, 'StorageLoc'), storage)) for m in mapping):
                reject(r, 4000, f'{file} |Warning : Storage Location Not available.', sku, wh)

    def clean_qty(file, sku, wh, quantities, deletion=True):
        rows = files[file]
        for r in rows:
            _set(r, sku, _trim(_v(r, sku)))
            _set(r, wh, _trim(_v(r, wh)))
            for q in quantities:
                _set(r, q, _trim(_v(r, q), commas=True))
        for suffix, code, word in ((True, 1000, 'Succeeding'), (False, 2000, 'Preceeding')):
            rejected = [r for r in rows if any((str(_v(r, q)).endswith('-') if suffix else str(_v(r, q)).startswith('-'))
                                                 for q in quantities if _v(r, q) is not None)]
            for r in rejected:
                reject(r, code, f'This SKU-Loc contains Qty with {word} minus in {file} file.', sku, wh)
            if deletion:
                rows[:] = [r for r in rows if r not in rejected]
        return rows

    stock = clean_qty('STOCK_ON_HAND', 'SKUCode', 'WHCode',
                      ('Unrestrictedstock', 'BlockedStock', 'QualityStock', 'ReservedStock'))
    stock_data, git_data, transit_data = [], [], []
    stock_fields = ('Unrestrictedstock', 'BlockedStock', 'QualityStock', 'ReservedStock')
    for r in stock:
        for m in mappings(_v(r, 'WHCode')):
            if not any(_v(r, f) is not None for f in stock_fields):
                continue
            for target, output in (('STK', stock_data), ('GIT', git_data)):
                qty = Decimal(0)
                for f in stock_fields:
                    flag = _v(m, f)
                    if flag in (target, '-' + target):
                        value = _decimal(_v(r, f)) or Decimal(0)
                        qty += -value if flag.startswith('-') else value
                for sku in old_map(_v(r, 'SKUCode'), _v(m, 'VectorLocation')):
                    output.append(dict(SKUCode=sku, WhCode=_v(m, 'VectorLocation'), Qty=qty,
                                       InputFileName='STOCK_ON_HAND'))
    for r in stock_data:
        if not any(_eq(_v(r, 'SKUCode'), _v(d, 'SKUCode')) and _eq(_v(r, 'WhCode'), _v(d, 'WhCode')) for d in daily):
            reject(r, 3000, 'STOCK_ON_HAND |Warning : SKU-Loc not defined in NMS.')
    missing_storage(stock, 'STOCK_ON_HAND', wh='WHCode')

    transit = clean_qty('In_Transit_Stok', 'SKUCode', 'WhCode', ('StockinTransit',))
    for r in files['Plant_Wip']:
        _set(r, 'SKuCode', _trim(_v(r, 'SKuCode')))
        _set(r, 'SKuCode', _leading_zero(_v(r, 'SKuCode')))
    wip = clean_qty('Plant_Wip', 'SKuCode', 'WhCode', ('BalanceQty',))
    indent = files['Indent_Report']
    for r in indent:
        for field in ('Material', 'Supp.Plant'):
            _set(r, field, _trim(_v(r, field)))
        for field in ('Str Loc', 'Rcv. Plant', 'Dlv but not PGI'):
            _set(r, field, _trim(_v(r, field), commas=True))
    for r in list(indent):
        q = _v(r, 'Dlv but not PGI')
        if q is not None and str(q).endswith('-'):
            reject(r, 1000, 'This SKU-Loc contains Qty with Succeeding minus in Indent_Report file.', 'Material', 'Rcv. Plant')
            indent.remove(r)
    for r in indent:
        q = _v(r, 'Dlv but not PGI')
        if q is not None and str(q).startswith('-'):
            reject(r, 2000, 'This SKU-Loc contains Qty with Preceeding minus in Indent_Report file.', 'Material', 'Rcv. Plant')
        if q is not None and _decimal(q) < 0:
            _set(r, 'Dlv but not PGI', '0')

    for r in transit:
        pgi = _date105(_v(r, 'DateofPGICreation'))
        if pgi < today - timedelta(days=30):
            continue
        for m in mappings(_v(r, 'WhCode')):
            if _v(r, 'StockinTransit') is None:
                continue
            for sku in old_map(_v(r, 'SKUCode'), _v(m, 'VectorLocation')):
                item = dict(SKUCode=sku, WhCode=_v(m, 'VectorLocation'),
                            Qty=_decimal(_v(r, 'StockinTransit')),
                            FromLocId=_trim(_v(r, 'FromLocId')),
                            DateofPGICreation=pgi, InputFileName='In_Transit_Stok')
                transit_data.append(item)
                git_data.append({k: item[k] for k in ('SKUCode', 'WhCode', 'Qty', 'InputFileName')})
    for r in wip:
        for m in mappings(_v(r, 'WhCode')):
            if _v(r, 'BalanceQty') is not None:
                for sku in old_map(_v(r, 'SKuCode'), _v(m, 'VectorLocation')):
                    git_data.append(dict(SKUCode=sku, WhCode=_v(m, 'VectorLocation'),
                                         Qty=_decimal(_v(r, 'BalanceQty')), InputFileName='Plant_Wip'))

    def indent_matches(master_row, field):
        wh = _v(master_row, 'WhCode')
        base, suffix = _split(wh)
        for r in indent:
            source = _v(r, field)
            source_wh = None if source is None else source + ('_' + str(_v(r, 'Str Loc')) if suffix else '')
            if _eq(source_wh, wh):
                for sku in old_map(_v(r, 'Material'), source, reverse=True):
                    if _eq(sku, _v(master_row, 'SKUCode')) and _v(r, 'Dlv but not PGI') is not None:
                        yield r

    virtual_git_candidates = defaultdict(list)
    for a in raw:
        if any(_has(_v(a, 'LocationType'), _v(t, 'LocationType')) for t in indent_types if _v(t, 'LocationType') is not None):
            for r in indent_matches(a, 'Rcv. Plant'):
                git_data.append(dict(SKUCode=_v(a, 'SKUCode'), WhCode=_v(a, 'WhCode'),
                                     Qty=_decimal(_v(r, 'Dlv but not PGI')), InputFileName='Indent_Report'))
    stock_totals, git_totals = defaultdict(list), defaultdict(list)
    for r in stock_data:
        stock_totals[_key(r)].append(_v(r, 'Qty'))
    for r in git_data:
        git_totals[_key(r)].append(_v(r, 'Qty'))
    for d in daily:
        k = _key(d)
        if k in stock_totals:
            deduction = Decimal(0)
            for a in raw:
                if (_eq(_v(a, 'SKUCode'), k[0]) and _eq(_v(a, 'WhCode'), k[1]) and
                        any(_has(_v(a, 'LocationType'), label) for label in ('RDC', 'CDC', 'Plant'))):
                    deduction += sum((_decimal(_v(r, 'Dlv but not PGI')) for r in indent_matches(a, 'Supp.Plant')), Decimal(0))
            d['Stock'] = _round(sum(stock_totals[k], Decimal(0)) - deduction)
        if k in git_totals:
            d['GIT'] = _round(sum((q for q in git_totals[k] if q is not None), Decimal(0))) if any(q is not None for q in git_totals[k]) else None
    for r in git_data:
        if not any(_eq(_v(r, 'SKUCode'), _v(d, 'SKUCode')) and _eq(_v(r, 'WhCode'), _v(d, 'WhCode')) for d in daily):
            reject(r, 3000, f"{_v(r, 'InputFileName')} |Warning : SKU-Loc not defined in NMS.")
    missing_storage(transit, 'In_Transit_Stok')
    missing_storage(wip, 'Plant_Wip')

    consumption = files['Consumption_ReceiptFile']
    for r in consumption:
        for f in ('SKU Code', 'Loc Code'):
            _set(r, f, _trim(_v(r, f)))
        for f in ('Storage Loc', 'Consumption', 'Production', 'Reciept(Goods recieved)', 'Reciept'):
            _set(r, f, _trim(_v(r, f), commas=True))
        _set(r, 'SKU Code', _leading_zero(_v(r, 'SKU Code')))
        if not any(_eq(_v(r, 'SKU Code'), _v(d, 'SKUCode')) and _eq(_v(r, 'Loc Code'), _v(d, 'WhCode')) for d in daily):
            reject(r, 3000, 'Consumption_ReceiptFile |Warning : SKU-Loc not defined in NMS.', 'SKU Code', 'Loc Code')
        if _v(r, 'Storage Loc') == '' and not any(_eq(_v(r, 'Loc Code'), _v(m, 'LocCode')) for m in mapping):
            reject(r, 4000, 'Consumption_ReceiptFile |Warning : Storage Location Not available.', 'SKU Code', 'Storage Loc')
        for pair in (('Consumption', 'Production'), ('Reciept', 'Reciept(Goods recieved)')):
            if any(_v(r, f) is not None and (str(_v(r, f)).startswith('-') or str(_v(r, f)).endswith('-')) for f in pair):
                reject(r, 1000, 'This SKU-Loc contains Qty with Preceeding or Succeeding minus in Consumption_ReceiptFile', 'SKU Code', 'Loc Code')
                for f in pair:
                    _set(r, f, '0')
    for d in daily:
        values = []
        receipts = []
        for a in raw:
            if not (_eq(_v(a, 'SKUCode'), _v(d, 'SKUCode')) and _eq(_v(a, 'WhCode'), _v(d, 'WhCode'))):
                continue
            base, suffix = _split(_v(a, 'WhCode'))
            for r in consumption:
                if _eq(_v(r, 'SKU Code'), _v(a, 'SKUCode')) and _eq(_v(r, 'Loc Code'), base) and (suffix == '' or _eq(_v(r, 'Storage Loc'), suffix)):
                    values.append(_decimal(_v(r, 'Consumption'), 2, True) + _decimal(_v(r, 'Production'), 2, True))
                    receipts.append(_decimal(_v(r, 'Reciept'), 2, True) + _decimal(_v(r, 'Reciept(Goods recieved)'), 2, True))
        if values:
            d['Consumption'] = _round(sum(values, Decimal(0)))
            d['Receipts'] = _round(sum(receipts, Decimal(0)))

    # SQL LIKE 'V_%' uses '_' as one-character wildcard. It therefore excludes
    # every WhCode beginning with V and at least one further character.
    for v in daily:
        candidates = [x for x in daily if _eq(_v(x, 'SKUCode'), _v(v, 'SKUCode'))
                      and _eq(_v(v, 'WhCode'), 'V_' + str(_v(x, 'WhCode')))
                      and not (str(_v(x, 'WhCode')).startswith('V') and len(str(_v(x, 'WhCode'))) > 1)]
        if len({str(x['Stock']) for x in candidates}) > 1:
            ambiguity.append(f'virtual Stock UPDATE FROM: {_key(v)}')
        elif candidates:
            v['Stock'] = candidates[0]['Stock']

    for a in raw:
        alt = _v(a, 'SKULocAtt01')
        if alt in (None, ''):
            continue
        k = _key(a)
        def from_match(source, value):
            return source is not None and value is not None and (_eq(source, value) or ('_' not in str(value) and str(source).casefold().startswith(str(value).casefold() + '_')))
        rlt = _decimal(_v(a, 'RLT'), 0) if _v(a, 'RLT') is not None else None
        qty2_values = [t['Qty'] or Decimal(0) for t in transit_data if _key(t) == k and
                       from_match(_v(t, 'FromLocId'), _v(a, 'ParentWhCode')) and
                       rlt is not None and qty2_days is not None and
                       rlt - Decimal((today - _v(t, 'DateofPGICreation')).days) <= Decimal(qty2_days)]
        qty3_values = [t['Qty'] or Decimal(0) for t in transit_data if _key(t) == k and from_match(_v(t, 'FromLocId'), alt)]
        qty2 = sum(qty2_values, Decimal(0)) if sum(qty2_values, Decimal(0)) > 0 else None
        qty3 = sum(qty3_values, Decimal(0)) if sum(qty3_values, Decimal(0)) > 0 else None
        alt_qty = []
        for t in indent_types:
            if not _has(_v(a, 'LocationType'), _v(t, 'LocationType')):
                continue
            for r in indent:
                receiving = _v(r, 'Rcv. Plant')
                supplying = _v(r, 'Supp.Plant')
                suffix = _v(r, 'Str Loc')
                if (_eq(_v(r, 'Material'), k[0]) and receiving is not None and supplying is not None
                        and _eq(receiving + ('_' + str(suffix) if '_' in str(k[1]) else ''), k[1])
                        and _eq(supplying + ('_' + str(suffix) if '_' in str(alt) else ''), alt)):
                    q = _decimal(_v(r, 'Dlv but not PGI'), 3, True)
                    alt_qty.append(q)
        qty7 = sum(alt_qty, Decimal(0)) if sum(alt_qty, Decimal(0)) > 0 else None
        if any(x is not None for x in (qty2, qty3, qty7)):
            virtual_git_candidates[(k[0], 'V_' + str(k[1]))].append(
                sum((x or Decimal(0) for x in (qty2, qty3, qty7)), Decimal(0)))
    for d in daily:
        candidates = virtual_git_candidates.get(_key(d), [])
        if len(set(candidates)) > 1:
            ambiguity.append(f'virtual GIT UPDATE FROM: {_key(d)}')
        elif candidates:
            d['GIT'] = candidates[0]

    for a in raw:
        quantities = [r['Qty'] for r in git_data if r['InputFileName'] == 'Indent_Report' and _key(r) == _key(a)]
        if quantities:
            _set(a, 'SKULocAtt06', sum((q for q in quantities if q is not None), Decimal(0)) if any(q is not None for q in quantities) else None)
    for a in attrs:
        hits = [r for r in raw if _eq(_v(a, 'SKUCode'), _v(r, 'SKUCode')) and _eq(_v(a, 'LocCode'), _v(r, 'WhCode'))]
        if len({(_v(r, 'SKULocAtt03'), _v(r, 'SKULocAtt06')) for r in hits}) > 1:
            ambiguity.append(f'SkuLocAttributeData UPDATE FROM: {_key(a, "LocCode")}')
        if hits:
            _set(a, 'c3', _v(hits[0], 'SKULocAtt03'))
            _set(a, 'c6', _v(hits[0], 'SKULocAtt06'))
    for a in standards:
        hits = [(p, u) for p in price if _key(p) == _key(a)
                for u in ([x for x in uom if _key(x) == _key(a)] or [None])]
        candidates = [(None if _v(p, 'Price') is None else _round(Decimal(str(_v(p, 'Price'))) * Decimal(str(_v(u, 'SAPToVectorConversionFactor') if u and _v(u, 'SAPToVectorConversionFactor') is not None else 1)), 3), _v(p, 'SLT')) for p, u in hits]
        if len(set(candidates)) > 1:
            ambiguity.append(f'SKULocStandardAttributes UPDATE FROM: {_key(a)}')
        if candidates:
            _set(a, 'Price', candidates[0][0])
            _set(a, 'SLT', candidates[0][1])

    orders = files['OPEN_SALES_ORDER']
    grouped = defaultdict(list)
    for r in orders:
        for f in ('SKuCode', 'WhCode', 'CustomerNo'):
            _set(r, f, _trim(_v(r, f)))
        for f in ('OrderDate', 'BalanceQty', 'SalesOrder'):
            _set(r, f, _trim(_v(r, f), commas=True))
        if _v(r, 'BalanceQty') is not None and '-' in str(_v(r, 'BalanceQty')):
            _set(r, 'BalanceQty', '0')
        for m in mappings(_v(r, 'WhCode')) or [None]:
            mapped_wh = _v(m, 'VectorLocation') if m else _v(r, 'WhCode')
            days = _v(m, 'DaystobeConsidered') if m else None
            days = 90 if days in (None, '') else int(days)
            order_date = _date105(_v(r, 'OrderDate'))
            if order_date >= today - timedelta(days=days):
                grouped[(_v(r, 'CustomerNo'), _v(r, 'OrderDate'), _v(r, 'SKuCode'), mapped_wh, _v(r, 'SalesOrder'))].append(_decimal(_v(r, 'BalanceQty')))
    pso = [dict(OrderId=k[4], SKUCode=k[2], WhCode=k[3], Qty=_round(sum(v, Decimal(0))),
                Extra=None) for k, v in grouped.items()]

    distinct_bom = set()
    for b in files['BOM_Detail']:
        distinct_bom.add((_v(b, 'Material'), _v(b, 'Component'), _v(b, 'Plant'), float(_v(b, 'Quantity'))))
    bom_groups = defaultdict(list)
    for fg, pm, wh, multiplier in distinct_bom:
        bom_groups[(fg, pm, wh)].append(multiplier)
    pm_groups = defaultdict(list)
    for b in bor:
        dispatch = _decimal(_v(b, 'DispatchQty'))
        if dispatch is None or dispatch <= 0:
            continue
        masters = [x for x in raw if _key(x) == _key(b)] or [None]
        for master_row in masters:
            pack = _v(master_row, 'Packsize') if master_row else None
            pack = Decimal(str(pack)) if pack is not None else Decimal(1)
            for (fg, pm, wh), candidates in bom_groups.items():
                if _eq(fg, _v(b, 'SKUCode')) and _eq(wh, _v(b, 'WhCode')):
                    if len(set(candidates)) > 1:
                        ambiguity.append(f'BOM FIRST_VALUE peer: {fg}/{pm}/{wh}')
                        continue
                    for _ in candidates:  # DISTINCT rows remain duplicated by cteValidBOMData.
                        # B.Multiplier is FLOAT, so SQL promotes this arithmetic
                        # before ROUND; retain that stage instead of decimal math.
                        qty = _round(Decimal(str(1.0 * float(dispatch) * candidates[0] / float(pack))))
                        pm_groups[(str(pm) + '_' + str(fg) + '_' + str(wh), pm, _v(b, 'WhCode'))].append(qty)
    pso.extend(dict(OrderId=k[0], SKUCode=k[1], WhCode=k[2], Qty=_round(sum(v, Decimal(0))), Extra=None)
               for k, v in pm_groups.items())
    return dict(status='AMBIGUOUS' if ambiguity else 'SOURCE_KNOWN', ambiguity=sorted(set(ambiguity)),
                DailyDataRaw=[dict(SKUCode=d['SKUCode'], WhCode=d['WhCode'], Stock=d['Stock'],
                                   Consumption=d['Consumption'], GIT=d['GIT'], Receipts=d['Receipts'],
                                   PSO=None, ReportDate=today) for d in daily],
                PSOData=pso, RejectedMaster=rejections, interface_tables=files,
                In_Transit_Stok_Data=transit_data, MasterDataRaw=raw,
                SkuLocAttributeData=attrs, SKULocStandardAttributes=standards,
                GulfOil_StockData=stock_data, GulfOil_GITData=git_data)
