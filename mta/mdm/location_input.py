"""Bounded Location approved-input adapter for pinned NMSImportData.sql."""
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
import hashlib
import json

from django.db import connection

from mta.mdm.location import ALIASES
from mta.mdm.task_reads import sql_key
from mta.runtime.mdm_models import (MdmLocationAttributes, MdmLocationDescription,
    MdmLocationApproved)

SQL_DIGEST = 'c86d014b1f7ee921821f83936a53d1d4da566ba9b2558db9252853260c3c3801'
LOCATION_FIELDS = tuple(name for name in ALIASES.values() if name != 'WHCode')


@dataclass(frozen=True)
class LocationInputRevision:
    digest: str
    source_digest: str
    attributes: tuple
    descriptions: tuple
    approved: tuple


def select_revision(source, expected_digest=None):
    expressions, params = [], []
    for label, model, columns, owner in (
        ('attributes', MdmLocationAttributes, [n for n in ALIASES.values() if n != 'WHDescription'], True),
        ('descriptions', MdmLocationDescription, ['WHCode', 'WHDescription'], True),
        ('approved', MdmLocationApproved, [*ALIASES.values(), 'ActionType', 'Approved', 'Reverted'], False)):
        table = connection.ops.quote_name(model._meta.db_table)
        selected = ','.join(connection.ops.quote_name(name) for name in columns)
        where = " AND owner='Importer'" if owner else ''
        expressions.append("%s,(SELECT coalesce(json_agg(row_to_json(r)),'[]'::json) FROM (SELECT " +
            selected + ' FROM ' + table + ' WHERE source_id=%s' + where + ' ORDER BY id) r)')
        params.extend([label, source.pk])
    with connection.cursor() as cursor:
        cursor.execute('SELECT json_build_object(' + ','.join(expressions) + ')::text', params)
        raw = cursor.fetchone()[0]
    digest = hashlib.sha256((source.digest + '\n' + SQL_DIGEST + '\n' + raw).encode()).hexdigest()
    if expected_digest is not None and digest != expected_digest:
        raise ValueError('approved Location input revision changed')
    rows = json.loads(raw)
    return LocationInputRevision(digest, source.digest, *(tuple(MappingProxyType(row)
        for row in rows[name]) for name in ('attributes', 'descriptions', 'approved')))


def unique_update(rows, code):
    matches = [row for row in rows if sql_key(row['WHCode']) == sql_key(code)]
    if matches and any(row != matches[0] for row in matches[1:]):
        raise ValueError('canonical Location UPDATE has incomparable duplicate source values')
    return matches[0] if matches else None


def consumer_input(revision, master_rows, master_columns, *, nms_active):
    """Apply only the Location portion of NMSImportData to supplied raw rows."""
    result = deepcopy(list(master_rows))
    if not nms_active:
        return result
    def blank(): return dict.fromkeys(master_columns)
    codes = {sql_key(row.get('WhCode')) for row in result}
    additions = []
    for description in revision.descriptions:
        if sql_key(description['WHCode']) not in codes:
            row = {**blank(), 'WhCode': description['WHCode'],
                   'WHDescription': description['WHDescription']}
            if row not in additions: additions.append(row)
    result += additions
    codes = {sql_key(row.get('WhCode')) for row in result}
    additions = []
    for staged in revision.approved:
        if staged['Approved'] and staged['ActionType'] == 1 and sql_key(staged['WHCode']) not in codes:
            row = {**blank(), 'WhCode': staged['WHCode'], **{name: staged[name]
                for name in ('WHDescription', 'LocationType', 'LogisticsLocation',
                             *('LL' + str(i) for i in range(1, 6)))}}
            if row not in additions: additions.append(row)
    result += additions
    deleted = {sql_key(row['WHCode']) for row in revision.approved
               if row['Approved'] and row['ActionType'] == 0}
    result = [row for row in result if row.get('WhCode') is None or
              sql_key(row['WhCode']) not in deleted]
    overlay = [row for row in revision.approved if row['Approved'] and row['ActionType'] == 1]
    # LocationMaster is a FULL OUTER JOIN of SiteDescriptionTbl and the queue.
    # Attribute-only/raw-only codes therefore never enter the update join.
    location_master_codes = {sql_key(row['WHCode']) for row in
        (*revision.descriptions, *revision.approved)}
    for row in result:
        code = row.get('WhCode')
        if code is None or sql_key(code) not in location_master_codes:
            continue
        attr = unique_update(revision.attributes, code)
        description = unique_update(revision.descriptions, code)
        approved = unique_update(overlay, code)
        for name in LOCATION_FIELDS:
            target = 'LocAtt' + name[1:].zfill(2) if name.startswith('c') else name
            if approved is not None:
                row[target] = approved[name]
            elif name == 'WHDescription':
                row[target] = description[name] if description is not None else None
            elif attr is not None:
                row[target] = attr[name]
    return result
