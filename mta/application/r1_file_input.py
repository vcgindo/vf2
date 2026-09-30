"""Selected CSV landing contract from canonical ReadDailyDataToInterface.py.

Pure source-input adapter, not calculated rows. Missing files leave freshly
cleared tables empty; parser failure clears the entire selected landing batch.
Database conversion/site transformation remain separate producer boundaries.
"""
import csv
from datetime import date, timedelta
from io import StringIO
import re

PANDAS_NA_TOKENS = frozenset(('', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN',
                            '-NaN', '-nan', '1.#IND', '1.#QNAN', '<NA>', 'N/A', 'NA',
                            'NULL', 'NaN', 'None', 'n/a', 'nan', 'null'))


def date_tokens(day):
    value = date.fromisoformat(day)
    previous = value - timedelta(days=1)
    return {'ddmmyyyy': value.strftime('%d%m%Y'), 'dd-mm-yyyy': value.strftime('%d-%m-%Y'),
            'yyyymmdd': value.strftime('%Y%m%d'), 'yyyy_mm_dd': value.strftime('%Y_%m_%d'),
            'dmyyyy': f'{value.day}{value.month}{value.year}', 'ddmmyy': value.strftime('%d%m%y'),
            'dd_mm_yyyy': value.strftime('%d_%m_%Y'), 'yyyy_mm_dd-1': previous.strftime('%Y_%m_%d'),
            'yyyymmdd-1': previous.strftime('%Y%m%d')}


def map_csv_inputs(mapping, files, business_date):
    """files is an ordered list of {name, content(bytes), encoding} facts.

    Encoding must be supplied by the inspected input detector; this adapter
    never guesses a new encoding policy. Only the selected CSV contract is
    implemented here; other formats are explicitly unsupported, not empty PASS.
    """
    groups = {}
    for row in mapping:
        name = row['FileName'].format(**date_tokens(business_date))
        if name not in groups:
            groups[name] = dict(table=row['TableName'], columns=[], delimiter=row['Delimiter'])
        groups[name]['columns'].append(row['Col'])
    tables = {r['TableName']: [] for r in mapping}
    processed, missing = [], []
    try:
        for fixed in groups:
            matches = [f for f in files if re.fullmatch(re.escape(fixed) + '.*', f['name'])]
            if not matches:
                missing.append(fixed)
            for source in matches:
                # Canonical first-prefix selection is distinct from scan match.
                key = next(k for k in groups if source['name'].startswith(k))
                group = groups[key]
                if source['name'].rsplit('.', 1)[-1].lower() != 'csv':
                    raise ValueError('Unsupported selected format; not certified: ' + source['name'])
                text = source['content'].decode(source['encoding'])
                if not text.strip():
                    raise ValueError('No columns to parse from file')
                reader = csv.DictReader(StringIO(text), delimiter=group['delimiter'])
                headers = reader.fieldnames or []
                if len(headers) != len(set(headers)):
                    raise ValueError('Duplicate CSV headers require canonical discrimination')
                absent = [c for c in group['columns'] if c not in headers]
                if absent:
                    raise ValueError('Missing columns: ' + ', '.join(absent))
                rows = []
                for row in reader:
                    if None in row:
                        raise ValueError('Extra CSV values require canonical discrimination')
                    values = [(row.get(c) or '') for c in group['columns']]
                    if any(value != value.strip() for value in values):
                        raise ValueError('Whitespace behavior requires canonical pandas version; input not certified')
                    rows.append(['' if value in PANDAS_NA_TOKENS else value for value in values])
                tables[group['table']].extend(rows)
                processed.append(dict(name=source['name'], table=group['table'], rows=len(rows)))
    except (ValueError, UnicodeError, csv.Error) as error:
        return dict(status='FAILED_INPUT', tables={name: [] for name in tables},
                    processed=processed, missing=missing, error=str(error))
    return dict(status='VALIDATED', tables=tables, processed=processed, missing=missing)
