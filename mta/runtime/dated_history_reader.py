"""Direct indexed reads of one accepted dated-history cut; no ancestry walk."""
import json

from django.db import connection

from mta.row_sequences import RecordRows
from mta.serialization import digest
from mta.runtime.dated_history_delta import FAMILIES, Occurrence, supports_descriptor, source_table
from mta.runtime.rationing_reader import Cut, CUT_FIELDS, IMAGE_KEYS
from mta.runtime.relational_state import quote, wire_value
from mta.runtime.state_cut_models import OperationalStateCut


FORMAT = 'dated-history-occurrences-v1'
ROOT_KEYS = frozenset(('format','cut','initialization','family','position','run','parent','parent_root',
    'input_digest','settings_digest','fields','count','inserted','removed','facts_digest','removals_digest','anchor'))


def table(family):
    if family not in FAMILIES:
        raise ValueError('Unqualified dated history family')
    return 'mta_state.history_' + source_table(family).replace('/','_').lower()


def read_cut(identity):
    row = OperationalStateCut.objects.values(*CUT_FIELDS).get(pk=identity)
    return authenticate_cut(row)


def authenticate_cut(row):
    """Also authenticates headers fetched together by the explicit audit."""
    if not row['root_body'] or row['run_id'] and row['run__status'] != 'SUCCEEDED':
        raise ValueError('History requires its accepted sealed cut')
    body = json.loads(row['root_body'])
    expected = dict(format=FORMAT, cut=str(row['id']), initialization=str(row['initialization_id']),
        family=row['family'], position=row['position'], run=str(row['run_id']) if row['run_id'] else None,
        parent=str(row['parent_id']) if row['parent_id'] else None,
        input_digest=row['input_digest'], settings_digest=row['settings_digest'])
    if (type(body) is not dict or set(body) != ROOT_KEYS or row['family'] not in FAMILIES
            or any(type(body[k]) is not type(v) or body[k] != v for k,v in expected.items())
            or digest(body) != row['root_digest']
            or not supports_descriptor(row['family'],body['fields'],body['count'])):
        raise ValueError('History cut commitment differs')
    return Cut(row['id'],row['initialization_id'],row['run_id'],row['position'],row['root_digest'],body)


def image_metadata(cut):
    family = cut.body['family']
    return dict(image=family,table=source_table(family),count=cut.body['count'],
        digest=cut.root_digest,fields=cut.body['fields'],storage_format=FORMAT,cut_id=str(cut.identity))


def owns(item):
    return item.get('storage_format') == FORMAT


def require_image(run,item):
    if type(item) is not dict or set(item) != IMAGE_KEYS or not owns(item):
        raise ValueError('Unknown dated history image metadata')
    cut = read_cut(item['cut_id'])
    if cut.run != run.pk or image_metadata(cut) != item:
        raise ValueError('History image differs from its exact run and cut')
    return cut


def occurrence_relation(cut,names=None):
    """Unnumbered visible occurrences; selective consumers filter this first."""
    fields = cut.body['fields']
    if names is not None:
        by_name = {d[0]:d for d in fields}
        if len(set(names)) != len(names) or not set(names) <= by_name.keys():
            raise ValueError('Unknown or repeated history projection field')
        fields = [by_name[n] for n in names]
    sql = ('SELECT born_position,vf_ordinal'+(' ,'+','.join(quote(n) for _,n,_ in fields) if fields else '')+
        ' FROM '+table(cut.body['family'])+" WHERE initialization_id=%s AND int8range(born_position,end_position,'[)') @> %s::bigint"
        )
    return sql,[cut.initialization,cut.position],fields


def occurrence_query(cut,names=None):
    sql,params,fields = occurrence_relation(cut,names)
    return sql+' ORDER BY born_position,vf_ordinal',params,fields


def image_relation(run,item,*,required_fields=None):
    """Full logical image with dense consumer ordinals, not birth identities.

    Pair/date graph reads use occurrence_relation directly: putting their filter
    above this window would number the complete history before selection.
    """
    cut = require_image(run,item)
    fields = cut.body['fields']
    names = None
    if required_fields is not None:
        by_column = {column:name for name,column,_ in fields}
        if not set(required_fields) <= by_column.keys():
            raise ValueError('Unknown history SQL projection column')
        names = [by_column[c] for c in dict.fromkeys(required_fields)]
    sql,params,fields = occurrence_relation(cut,names)
    projection = ''.join(','+quote(column) for _,column,_ in fields)
    return ('SELECT row_number() OVER (ORDER BY born_position,vf_ordinal)-1 AS vf_ordinal'+
            projection+' FROM ('+sql+') history_occurrences'),params


def iter_occurrences(cut,*,names=None):
    sql,params,fields = occurrence_query(cut,names)
    count = 0
    previous = None
    with connection.chunked_cursor() as cursor:
        cursor.execute(sql,params)
        while batch := cursor.fetchmany(500):
            for record in batch:
                occurrence = Occurrence(record[0],record[1])
                if occurrence.position > cut.position or previous is not None and occurrence <= previous:
                    raise ValueError('History occurrence order differs')
                previous = occurrence
                count += 1
                yield occurrence,{field:wire_value(value,kind) for (field,_,kind),value in zip(fields,record[2:])}
    if count != cut.body['count']:
        raise ValueError('History visible membership count differs')


def iter_image(run,item):
    for _,row in iter_occurrences(require_image(run,item)):
        yield row


def load_image(run,item):
    return load_cut(require_image(run,item))


def load_cut(cut,*,names=None):
    def records():
        return (row for _,row in iter_occurrences(cut,names=names))
    return RecordRows(cut.body['count'],records) if cut.body['count']>10000 else list(records())
