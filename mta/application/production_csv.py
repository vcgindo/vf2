"""Lossless ordinary CSV intake into the existing native daily envelope.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import csv
from datetime import datetime, date
import io
import json

from mta.application.operational_inputs import NULL, typed_value
from mta.application.production_csv_contract import SCHEMA_VERSION, feeds
from mta.application.native_daily_contract import SOURCE_SCHEMA, CONTROL_TABLES
from mta.serialization import storage


class CsvIntakeError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__('CSV intake rejected: ' + '; '.join(
            f"{r['file']}:{r.get('record', 0)}:{r.get('column', '')}: {r['message']}"
            for r in issues[:10]))


def parse_csv(raw, columns, filename):
    issues, output, ordinals = [], [], []
    try:
        text = raw.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(text, newline=''), strict=True)
        header = next(reader, None)
        expected = [c['name'] for c in columns]
        if header != expected:
            raise CsvIntakeError([dict(file=filename, record=0, column='',
                message='Header must match declared column names and order')])
        last_line = reader.line_num
        for ordinal, cells in enumerate(reader, 1):
            first_line, last_line = last_line + 1, reader.line_num
            if len(cells) != len(columns):
                issues.append(dict(file=filename, record=ordinal, line=first_line,
                                   column='', message='CSV row width differs'))
                continue
            row = {}
            for cell, column in zip(cells, columns):
                name, kind = column['name'], column['type']
                try:
                    value = None if cell == NULL else cell
                    if kind == 'datetimetz':
                        if value is None and not column['nullable']:
                            raise ValueError('NULL in required column: ' + name)
                        if value is not None:
                            value = datetime.fromisoformat(value)
                            if value.tzinfo is None:
                                raise ValueError('Timezone is required')
                    else:
                        value = typed_value(value, column)
                    row[name] = (value.isoformat() if isinstance(value, (date, datetime)) else
                                 str(value) if kind in ('decimal', 'numeric') and value is not None else value)
                except (ValueError, TypeError, OverflowError) as error:
                    issues.append(dict(file=filename, record=ordinal, line=first_line,
                        column=name, message=str(error)[:300]))
            output.append(row)
            ordinals.append(dict(record=ordinal, first_line=first_line, last_line=last_line))
    except CsvIntakeError:
        raise
    except (UnicodeError, csv.Error) as error:
        raise CsvIntakeError([dict(file=filename, record=len(output) + 1,
            column='', message=type(error).__name__ + ': ' + str(error)[:300])]) from error
    if issues:
        raise CsvIntakeError(issues)
    return output, ordinals


def batch_contract(value, binding, business_date):
    if date.fromisoformat(business_date).isoformat() != business_date:
        raise ValueError('Business date must use YYYY-MM-DD')
    if (not isinstance(value, dict) or set(value) != {'schema', 'batch_id', 'business_date', 'feeds'}
            or value['schema'] != SCHEMA_VERSION or value['business_date'] != business_date
            or not isinstance(value['batch_id'], str) or not 1 <= len(value['batch_id']) <= 120):
        raise ValueError('Complete dated CSV batch contract required')
    roster = feeds(binding['intake_schema'])
    if not isinstance(value['feeds'], dict) or set(value['feeds']) != set(roster):
        raise ValueError('Complete explicit CSV feed roster required')
    for filename, status in value['feeds'].items():
        if status != 'PRESENT' and not (filename == 'OrderFeed.csv' and status == 'MISSING'):
            raise ValueError('Unsupported feed availability: ' + filename)
    return roster


def assemble(batch, binding, payloads, *, first_day):
    """Only files own external facts; DB queues and successors keep their owners."""
    business_date = batch['business_date']
    date.fromisoformat(business_date)
    roster = batch_contract(batch, binding, business_date)
    required = {name for name, status in batch['feeds'].items() if status == 'PRESENT'}
    if set(payloads) != required:
        raise ValueError('Supplied CSV files differ from the batch declaration')
    validation = binding['validation']
    if (set(validation) != {'phase_controls_input_validation', 'seasonality_input_validation'}
            or any(type(v) is not bool for v in validation.values())):
        raise ValueError('Explicit native validation policy required')
    value = dict(schema=SOURCE_SCHEMA, intake_schema=binding['intake_schema'],
        consumer_opening=binding['consumer_opening'] if first_day else None,
        day=dict(business_date=business_date, order_feed_status=batch['feeds']['OrderFeed.csv'],
            new_force_requests=[], control_requests={k: [] for k in CONTROL_TABLES}, **validation),
        producer_sources=dict(schema=binding['producer_source_schema'],
            report_policy=binding['report_policy'],
            report_opening=binding['report_opening'] if first_day else None,
            shipments=dict(schema='daily-transit-raw-v1', business_date=business_date,
                provenance=dict(batch_id=batch['batch_id'], format=SCHEMA_VERSION), rows=[]),
            transporters=dict(schema='daily-transporter-raw-v1', business_date=business_date,
                provenance=dict(batch_id=batch['batch_id'], format=SCHEMA_VERSION), rows=[])))
    mappings, errors = {}, []
    for filename, spec in roster.items():
        try:
            rows, positions = (parse_csv(payloads[filename], spec['columns'], filename)
                if filename in payloads else ([], []))
            mappings[filename] = positions
            owner = value
            parts = spec['path'].split('/')
            for key in parts[:-1]:
                owner = owner.setdefault(key, {})
            owner[parts[-1]] = rows
        except CsvIntakeError as error:
            errors.extend(error.issues)
    if errors:
        raise CsvIntakeError(errors)
    raw = json.dumps(storage(value), ensure_ascii=False, sort_keys=True,
                     separators=(',', ':'), allow_nan=False).encode('utf-8')
    return raw, mappings
