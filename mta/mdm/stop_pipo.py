"""Pinned master-6 configuration and native Stop PIPO current projection."""
from decimal import Decimal
from itertools import product
import json
from pathlib import Path
import re
from types import SimpleNamespace

from mta.mdm.force_reads import _scope_count
from mta.mdm.task_reads import sql_key
from mta.presentation.context import PublicationUnavailable, selected_run
from mta.presentation.rrr_sql import like_pattern
from mta.presentation.selective import image_rows
from mta.runtime.mdm_stop_pipo_models import MdmStopPipoQueue


CONFIG = json.loads((Path(__file__).resolve().parents[1] /
                     'config/mdm_stop_pipo.json').read_text(encoding='utf-8'))
FIELDS = {row['Col_Code']: row for row in CONFIG['UI_MDMConfig']}
ALIASES = {alias: row['TableField'] for alias, row in FIELDS.items()}
DRAFT_ALIASES = dict(ALIASES, IsSelected='IsSelected')
NUMERIC = {'onm', 'cn', 'pcn', 'ptn', 'isPOActive'}


def configuration(screen_type):
    mapper = CONFIG['MasterMapper'][0]
    flag = {'add': 'IsAdd', 'modify': 'IsModify', 'remove': 'IsRemove'}.get(screen_type)
    if flag and not mapper[flag]:
        return []
    fields = [dict(displayName=row['Header'], key=alias,
        col_Position=str(row['Col_Position']), visible=row['Visible'],
        isAdd=row['IsAdd'], isEdit=row['IsEdit'], isDelete=row['IsDelete'],
        isDownload=row['IsDownload'], isApplicable=row['IsApplicable'],
        dataType=row['DataType']) for alias, row in FIELDS.items()]
    return [dict(id=str(mapper['MasterId']), name=mapper['MasterName'], fields=fields)]


def publication(source):
    from mta.mdm.stop_pipo_source import require_installed
    owner = require_installed(source)
    if owner.last_run_id is None:
        raise PublicationUnavailable('stop_pipo_has_no_committed_publication')
    run = selected_run()
    if run.pk != owner.last_run_id:
        raise PublicationUnavailable('stop_pipo_selected_run_owner_mismatch')
    return run


def _same(left, right, left_names=('SKUCode', 'WHCode'), right_names=None):
    right_names = right_names or left_names
    return all(left.get(a) is not None and right.get(b) is not None and
               sql_key(left[a]) == sql_key(right[b])
               for a, b in zip(left_names, right_names))


def _filter(row, item):
    alias, operator = item['attributeName'], item['op']
    actual = row[alias]
    wanted = '' if item.get('value') is None else item['value']
    if operator in ('hasValue', 'hasNoValue'):
        empty = actual is None or (actual == 0 if alias in NUMERIC
                                   else str(actual).strip(' ') == '')
        return not empty if operator == 'hasValue' else empty
    if operator in ('contains', 'startsWith', 'endsWith',
                    'Notcontains', 'NotstartsWith', 'NotendsWith'):
        if actual is None:
            return False
        pattern = ('%' if operator.endswith(('contains', 'endsWith')) else '') + str(wanted)
        pattern += '%' if operator.endswith(('contains', 'startsWith')) else ''
        matched = re.fullmatch(like_pattern(pattern), str(actual),
                               re.IGNORECASE | re.DOTALL) is not None
        return not matched if operator.startswith('Not') else matched
    if operator not in ('=', '!=', '<>', '>', '>=', '<', '<='):
        raise ValueError('unsupported MDM filter operator')
    if actual is None:
        return operator == '<>'
    if alias in NUMERIC:
        left, right = Decimal(str(actual)), Decimal(str(wanted) or '0')
    else:
        left, right = sql_key(str(actual)), sql_key(str(wanted))
    return {'=': lambda: left == right, '!=': lambda: left != right,
            '<>': lambda: left != right, '>': lambda: left > right,
            '>=': lambda: left >= right, '<': lambda: left < right,
            '<=': lambda: left <= right}[operator]()


def _latest_reason_102(logs):
    grouped = {}
    for row in logs:
        if row['NormChangeReason'] == 102:
            grouped.setdefault((sql_key(row['SKUCode']), sql_key(row['WHCode'])), []).append(
                row['NormChangeDate'])
    # The native RN=1 projection exposes only NormChangeDate. Equal maximum
    # dates are therefore observably identical; no source-row winner is needed.
    return {key: max(values, key=lambda value: (value is not None, str(value or '')))
            for key, values in grouped.items()}


def _matches(rows, row, left_names=('SKUCode', 'WHCode'), right_names=None):
    return [candidate for candidate in rows
            if _same(row, candidate, left_names, right_names)] or [None]


def _project(source, run, payload):
    phase_out = image_rows(run, 'closing/dbm/PhaseOutTbl')
    phase_in = image_rows(run, 'closing/dbm/PhaseInTbl')
    phase_map = image_rows(run, 'closing/control_aux/phase_map')
    sku_descriptions = image_rows(run, 'closing/dbm/SKUDescriptionTbl')
    location_descriptions = image_rows(run, 'closing/dbm/SiteDescriptionTbl')
    logs = _latest_reason_102(image_rows(run, 'closing/dbm/NormChangeLogTbl'))
    stopped = list(MdmStopPipoQueue.objects.filter(source=source).order_by('id')
                   .values('SKUCode', 'WhCode'))
    rows = []
    for phase in phase_out:
        multiplicity = _scope_count(source, SimpleNamespace(
            SKUCode=phase['SKUCode'], WhCode=phase['WHCode']), payload)
        if not multiplicity:
            continue
        out_descriptions = _matches(sku_descriptions, phase,
                                    ('SKUCode',), ('SKUCode',))
        in_descriptions = _matches(sku_descriptions, phase,
            ('PhaseInSKUCode',), ('SKUCode',))
        locations = _matches(location_descriptions, phase,
                             ('WHCode',), ('WHCode',))
        incoming = _matches(phase_in, phase,
            ('PhaseInSKUCode', 'WHCode'), ('SKUCode', 'WHCode'))
        stops = _matches(stopped, phase,
                         ('SKUCode', 'WHCode'), ('SKUCode', 'WhCode'))
        mappings = _matches(phase_map, phase,
            ('SKUCode', 'WHCode'), ('PhaseOutSKUCode', 'WhCode'))
        last_change = logs.get((sql_key(phase['SKUCode']), sql_key(phase['WHCode'])))
        for out_description, in_description, location, incoming_row, stop, mapping in product(
                out_descriptions, in_descriptions, locations, incoming, stops, mappings):
            projected = dict(
                sc=phase['SKUCode'],
                posn=None if out_description is None else out_description['SKUDescription'],
                wc=phase['WHCode'],
                ln=None if location is None else location['WHDescription'],
                onm=None if mapping is None else mapping['PhaseOutSKUOrigNorm'],
                cn=phase['NewNorm'],
                nc=last_change,
                pd=phase['PhaseOutStartDate'],
                pis=phase['PhaseInSKUCode'],
                pisn=None if in_description is None else in_description['SKUDescription'],
                pcn=None if incoming_row is None else incoming_row['NewNorm'],
                ptn=None if incoming_row is None else incoming_row['TargetNorm'],
                isPOActive=0 if stop is None else 1)
            rows.extend(dict(projected) for _ in range(multiplicity))
    return rows


def read(source, payload, *, count=False):
    if int(payload['id']) != 6:
        raise ValueError('MDM family is not delivered')
    if not payload.get('product_permissions') or not payload.get('location_permissions'):
        return '' if count else None
    rows = [row for row in _project(source, publication(source), payload)
            if all(_filter(row, item) for item in payload.get('filters') or [])]
    if count:
        return str(len(rows))
    # SQL defines no order within equal (isPOActive, sc) groups. Keep every
    # projected occurrence and add no WH/ordinal tie-break or parity claim.
    rows.sort(key=lambda row: (row['isPOActive'], sql_key(row['sc'])))
    # Deployed GetData case 6 ignores PaginationParameter and returns the full
    # ordered projection. Preserve that observable master-specific behavior.
    return [{field['key']: row[field['key']] for field in payload['fields']}
            for row in rows]
