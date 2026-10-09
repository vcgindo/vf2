"""Master-4/5 task projections at native supplier occurrence grain.

The deployed queries deliberately have different grains for SOB and the two
MOQ formats.  Requested/history duplicates therefore remain occurrences; no
business-key deduplication is performed here.
"""
from collections import defaultdict
from datetime import timedelta
import json

from mta.mdm.clock import database_now
from mta.mdm.drafts import omit_nulls, value
from mta.mdm.supplier import CONFIG, setting
from mta.mdm.supplier_tasks import key_names, models_for, row_key, scopes
from mta.mdm.task_reads import TaskDenied, assigned, displayed_date, header, sql_key
from mta.presentation.context import permission_catalogue
from mta.mdm.supplier_permissions import triples, hierarchy_key, scope
from mta.runtime.mdm_models import (MdmLocationAttributes, MdmLocationDescription,
                                    MdmSkuAttributes, MdmSkuDescription, MdmTask)


DECISIONS = {'3': 'Request approved', '4': 'Request approval reverted/ Rejected'}


def _master_id(value_):
    result = int(value_)
    if result not in (4, 5):
        raise ValueError('MDM family is not delivered')
    return result


def _fields(task, master_id, *, review):
    """GetColumnList: UI aliases in configured column-position order."""
    names = (task.ColumnList or '').split(',')
    if review:
        names.extend(('SKUDescription', 'WHDescription'))
    return [(row['Col_Code'], row['TableField']) for row in sorted(
        CONFIG[master_id]['UI_MDMConfig'], key=lambda item: item['Col_Position'])
        if row['TableField'] in names]


def _project(row, fields, *, sku_description=None, location_description=None):
    result = {}
    for alias, field in fields:
        if field == 'SKUDescription':
            item = sku_description
        elif field == 'WHDescription':
            item = location_description
        else:
            item = getattr(row, field)
        if item is not None:
            result[alias] = item
    return result


def _review_text(row, fields, *, sku_description=None, location_description=None):
    # FOR JSON PATH, WITHOUT_ARRAY_WRAPPER is returned by SQL as text.  With
    # duplicate correlated rows SQL emits comma-separated JSON objects.
    values = _project(row, fields, sku_description=sku_description,
                      location_description=location_description)
    def encode(value):
        if isinstance(value, float):
            # SQL Server FOR JSON float53 uses 16 significant decimal digits
            # and a signed three-digit exponent, including zero.
            mantissa, exponent = format(value, '.15e').split('e')
            return mantissa + 'e' + format(int(exponent), '+04d')
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                          allow_nan=False).replace('/', '\\/')
    return '{' + ','.join(encode(key) + ':' + encode(value) for key, value in values.items()) + '}'


def _permission_triples(kind, ids):
    return triples(kind, ids)


def _scope_multiplicity(source, row, master_id, payload):
    product_triples = _permission_triples('products', payload.get('product_permissions'))
    products = sum(product_triples[tuple(hierarchy_key(getattr(item, 'SL' + str(i))) for i in range(1, 4))]
        for item in MdmSkuAttributes.objects.filter(source=source, owner='Importer')
        if row.SKUCode is not None and sql_key(item.SKUCode) == sql_key(row.SKUCode))
    if master_id == 5:
        return products
    location_triples = _permission_triples('locations', payload.get('location_permissions'))
    locations = sum(location_triples[tuple(hierarchy_key(getattr(item, 'LL' + str(i))) for i in range(1, 4))]
        for item in MdmLocationAttributes.objects.filter(source=source, owner='Importer')
        if row.WhCode is not None and sql_key(item.WHCode) == sql_key(row.WhCode))
    return products * locations


def _descriptions(source, requests, master_id, *, download):
    if download:
        return {}, {}
    sku_codes = {sql_key(row.SKUCode) for row in requests}
    skus = defaultdict(list)
    for row in MdmSkuDescription.objects.filter(
            source=source, owner='Importer').order_by('id'):
        if sql_key(row.SKUCode) in sku_codes:
            skus[sql_key(row.SKUCode)].append(row.SKUDescription)
    locations = defaultdict(list)
    if master_id == 4:
        wh_codes = {sql_key(row.WhCode) for row in requests}
        for row in MdmLocationDescription.objects.filter(
                source=source, owner='Importer').order_by('id'):
            if sql_key(row.WHCode) in wh_codes:
                locations[sql_key(row.WHCode)].append(row.WHDescription)
    return skus, locations


def _ordered(rows, names, *, download, action_type):
    result = list(rows)
    # Native ROW_NUMBER is ascending on the leading keys.  SupplierCode is
    # descending for review and modify downloads, ascending for add/remove
    # downloads. Stable sorts preserve duplicate occurrence order.
    supplier_descending = not download or action_type == 2
    result.sort(key=lambda row: (sql_key(row.SupplierCode) is not None,
                                 sql_key(row.SupplierCode) or ''),
                reverse=supplier_descending)
    if 'WhCode' in names:
        result.sort(key=lambda row: (sql_key(row.WhCode) is not None,
                                     sql_key(row.WhCode) or ''))
    result.sort(key=lambda row: (sql_key(row.SKUCode) is not None,
                                 sql_key(row.SKUCode) or ''))
    return result


def details(source, payload, actor, *, download=False):
    task_id = value(payload, 'taskId')
    task = header(source, task_id)
    if task is None:
        return None
    master_id = _master_id(task.MasterId)
    if task.Actiontype not in (1, 2, 3):
        raise ValueError('native supplier task action is unsupported')
    _, requested_model, history_model, _, _ = models_for(source, master_id)
    names = key_names(source, master_id)
    fields = _fields(task, master_id, review=not download)
    if not fields:
        raise ValueError('native supplier task column list is empty')

    complete_history = list(history_model.objects.filter(
        source=source, TaskId=task_id).order_by('id'))
    if download:
        approver_id = str(value(payload, 'approverId'))
        requester = MdmTask.objects.filter(source=source, TaskID=task_id,
                                           RequesterId=str(actor['id'])).exists()
        selected = (approver_id == str(actor['id'])
                    and any(assigned(row.ApproverId, actor['id'])
                            for row in complete_history))
        if not requester and not selected:
            raise TaskDenied('task_download_actor_required')
        visible_history = [row for row in complete_history
                           if str(row.ApprovedBy) == approver_id]
    else:
        visible_history = [row for row in complete_history
                           if row.Status is None and assigned(row.ApproverId, actor['id'])]

    by_key = defaultdict(list)
    for row in visible_history:
        identity = row_key(row, names)
        if None not in identity:
            by_key[identity].append(row)
    requests = _ordered(requested_model.objects.filter(
        source=source, TaskId=task_id).order_by('id'), names,
        download=download, action_type=task.Actiontype)
    all_requests = list(requested_model.objects.filter(
        source=source, TaskId=task_id).order_by('id'))
    sku_descriptions, location_descriptions = _descriptions(
        source, requests, master_id, download=download)

    rows = []
    for requested in requests:
        identity = row_key(requested, names)
        if None in identity:
            continue
        multiplicity = 1 if download else _scope_multiplicity(
            source, requested, master_id, payload)
        sku_values = sku_descriptions.get(sql_key(requested.SKUCode), [None]) or [None]
        location_values = ([None] if master_id == 5 else
            location_descriptions.get(sql_key(requested.WhCode), [None]) or [None])
        for old in by_key[identity]:
            for sku_description in sku_values:
                for location_description in location_values:
                    for _ in range(multiplicity):
                        if task.Actiontype == 2:
                            same = lambda row: row_key(row, names) == identity
                            item = {
                                'new': ','.join(_review_text(row, fields,
                                    sku_description=sku_description,
                                    location_description=location_description)
                                    for row in all_requests if same(row)),
                                'old': ','.join(_review_text(row, fields,
                                    sku_description=sku_description,
                                    location_description=location_description)
                                    for row in complete_history if same(row)),
                            }
                        else:
                            item = _project(requested, fields,
                                sku_description=sku_description,
                                location_description=location_description)
                            status = DECISIONS.get(old.Status) if download else old.Status
                            if status is not None:
                                item['Status'] = status
                            if old.Comments is not None:
                                item['Comments'] = old.Comments
                        rows.append({'RN': len(rows) + 1, **item})
    paging = value(payload, 'paginationParameter')
    if paging is not None:
        page = int(value(paging, 'pageNumber'))
        size = int(value(paging, 'recordsPerPage'))
        rows = [row for row in rows
                if (page - 1) * size + 1 <= row['RN'] <= page * size]
    return [{'MasterId': master_id, 'data': rows}]


def count(source, task_id, actor):
    task = header(source, task_id)
    if task is None:
        return 0
    master_id = _master_id(task.MasterId)
    _, _, history_model, _, _ = models_for(source, master_id)
    return sum(assigned(row.ApproverId, actor['id']) for row in
               history_model.objects.filter(source=source, TaskId=task_id))


def _require_history_scope(source, master_id, sku_code, wh_code, payload):
    sku_scope, location_scope = scopes(source, payload)
    if sql_key(sku_code) not in sku_scope:
        raise TaskDenied('sku_scope_required')
    if 'WhCode' in key_names(source, master_id) and sql_key(wh_code) not in location_scope:
        raise TaskDenied('sku_location_scope_required')


def history(source, payload, actor):
    master_id = _master_id(value(payload, 'masterId'))
    sku_code = value(payload, 'skuCode')
    # C# string concatenation turns a null request property into ''. SQL NULL
    # WhCode therefore does not match the default master-4/5 predicate.
    wh_code = value(payload, 'whCode')
    wh_lookup = '' if wh_code is None else wh_code
    _require_history_scope(source, master_id, sku_code, wh_lookup, payload)
    _, requested_model, history_model, _, _ = models_for(source, master_id)

    tasks = list(MdmTask.objects.filter(source=source, MasterId=str(master_id))
        .exclude(TaskStatus='1').exclude(TaskStatus=None).order_by('PendingSince', 'id'))
    requests = list(requested_model.objects.filter(source=source).order_by('id'))
    selected = [(task, row) for task in tasks for row in requests
        if row.TaskId == task.TaskID and sql_key(row.SKUCode) == sql_key(sku_code)
        and sql_key(row.WhCode) == sql_key(wh_lookup)]
    names = {name for task, _ in selected for name in (task.ColumnList or '').split(',')}
    fields = [(row['Col_Code'], row['TableField']) for row in sorted(
        CONFIG[master_id]['UI_MDMConfig'], key=lambda item: item['Col_Position'])
        if row['TableField'] in names]
    if not fields:
        return None

    histories = list(history_model.objects.filter(source=source).order_by('id'))
    result = []
    for task, requested in selected:
        # TaskMasterHistory's default master join omits SupplierCode.
        matches = [row for row in histories if row.TaskId == task.TaskID
            and sql_key(row.SKUCode) == sql_key(requested.SKUCode)
            and sql_key(row.WhCode) == sql_key(requested.WhCode)] or [None]
        for old in matches:
            item = _project(requested, fields)
            item.update(TaskId=requested.TaskId,
                PendingSince=displayed_date(task.PendingSince),
                RequesterName=task.RequesterName,
                ApproverName=old.ApprovedBy if old is not None else None)
            result.append(omit_nulls(item))
    return sorted(result, key=lambda row: row.get('PendingSince') or '') or None


def history_skus(source, payload):
    master_id = _master_id(value(payload, 'masterId'))
    if payload.get('product_permissions') is None or payload.get('location_permissions') is None:
        raise ValueError('native permission lists are required')
    skus = {sql_key(code) for code in scope(source, MdmSkuAttributes,
        'SKUCode', 'SL', 'products', payload['product_permissions'])}
    whs = {sql_key(code) for code in scope(source, MdmLocationAttributes,
        'WHCode', 'LL', 'locations', payload['location_permissions'])}

    upper = database_now().replace(hour=0, minute=0, second=0, microsecond=0)
    task_ids = set(MdmTask.objects.filter(source=source, MasterId=str(master_id),
        Actiontype=2, PendingSince__gte=upper - timedelta(days=90),
        PendingSince__lte=upper).values_list('TaskID', flat=True))
    _, _, history_model, _, _ = models_for(source, master_id)
    result = {}
    for row in history_model.objects.filter(source=source,
                                             TaskId__in=task_ids).order_by('id'):
        pair = (sql_key(row.SKUCode), sql_key(row.WhCode))
        if pair[0] in skus and pair[1] in whs and pair not in result:
            result[pair] = {'SKUCode': row.SKUCode, 'WHCode': row.WhCode}
    return list(result.values())
