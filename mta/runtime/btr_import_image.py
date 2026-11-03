"""Accepted and audited readers for a source-backed operational BTR import."""
import hashlib

from django.db import connection

from mta.row_sequences import RecordRows
from mta.runtime import btr_import_relation as imports
from mta.runtime import relational_state as typed
from mta.serialization import canonical_parts


def owns(item):
    return item.get('storage_format') == imports.FORMAT


def _has_future(owner, day):
    with connection.cursor() as cursor:
        cursor.execute('SELECT EXISTS(SELECT FROM '+typed.table_sql('BTR/BPR')+
                       ' WHERE vf_run_id=%s AND vf_image=%s AND "ReportDate">%s)',
                       [owner,imports.HISTORY,day])
        return cursor.fetchone()[0]


def compatible_parent(run):
    """A first report cut can bootstrap from a physical import.

    Until its predecessor has supplied a reusable report directory keep this
    day's original physical anchor. Missing reporting never delays calculation.
    """
    from mta.runtime.models import DailyReportGeneration
    if run.predecessor_id is None:
        return False
    prior = DailyReportGeneration.objects.filter(run_id=run.predecessor_id,version=2,status='READY').values(
        'metadata__btr_calendar__anchor').first()
    if prior is None:
        return False
    anchor = prior['metadata__btr_calendar__anchor']
    return anchor is None or not _has_future(anchor['run'],anchor['day'])


def report_version(run):
    """The physical report handles anchors with observations dated in the future."""
    if run.evidence_mode!='production':
        return 1
    item = run.production_manifest['images'][imports.HISTORY]
    if owns(item):
        return 2 if compatible_parent(run) else 1
    if _has_future(run.pk,run.business_date):
        return 1
    # An older sealed report may refer to a physical anchor that contained a
    # future day. Rebase via the physical report for this transition.
    from mta.runtime.models import DailyReportGeneration
    if run.predecessor_id and DailyReportGeneration.objects.filter(run_id=run.predecessor_id,version=2).exists():
        return 2 if compatible_parent(run) else 1
    return 2


def _require(run, item):
    if (not owns(item) or item['table'] != 'BTR/BPR' or item['image'] != imports.HISTORY
            or run.status != 'SUCCEEDED' or run.production_manifest['images'].get(imports.HISTORY) != item):
        raise ValueError('BTR import image requires its accepted run and sealed sources')


def relation(run, item):
    _require(run,item)
    return imports.source_query(run,item['sources'])


def _records(run, item, *, audit):
    sql, params = imports.source_query(run,item['sources'])
    fields = item['fields']
    columns = ['vf_ordinal', *(typed.quote(column) for _,column,_ in fields)]
    count = 0
    checksum = hashlib.sha256(b'[') if audit else None
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT '+','.join(columns)+' FROM ('+sql+') history ORDER BY vf_ordinal', params)
        while batch := cursor.fetchmany(500):
            for ordinal,*values in batch:
                if ordinal != count:
                    raise ValueError('BTR import ordinal differs')
                row = {key:typed.wire_value(value,kind)
                       for (key,_,kind),value in zip(fields,values,strict=True)}
                if checksum is not None:
                    if count:
                        checksum.update(b',')
                    for part in canonical_parts(row):
                        checksum.update(part)
                count += 1
                yield row
    if count != item['count']:
        raise ValueError('BTR import population differs')
    if checksum is not None:
        checksum.update(b']')
        if checksum.hexdigest() != item['digest']:
            raise ValueError('BTR import values, types or multiplicity differ')


def iter_image(run,item,*,audit):
    _require(run,item)
    yield from _records(run,item,audit=audit)


def load(run,item,*,audit):
    _require(run,item)
    def records():
        return _records(run,item,audit=audit)
    if item['count']>10000:
        if audit:
            for _ in records():
                pass
        return RecordRows(item['count'],records)
    return list(records())


def save(run, rows, current_image):
    """No closing history INSERT. Compare the complete original producer once."""
    sources = imports.advance(run,run.predecessor,current_image)
    columns = {name.casefold():(name,kind) for name,kind in typed.STORAGE_TABLES['BTR/BPR']}
    item,_,_ = typed.describe_rows(rows,columns,imports.HISTORY)
    item.update(table='BTR/BPR',storage_format=imports.FORMAT,sources=sources)
    for _ in _records(run,item,audit=True):
        pass
    return item
