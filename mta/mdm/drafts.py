"""Owned SKU drafts, preserving deployed text rows and statement boundaries."""
from datetime import datetime
from zoneinfo import ZoneInfo
import json

from django.conf import settings
from django.db.models import Max
from mta.runtime.mdm_models import MdmDraft, MdmDraftMaster, MdmDraftSku
from mta.mdm.sku import ALIASES, FIELDS


class DraftDenied(Exception):
    pass


def value(payload, name, default=None):
    return next((v for k, v in payload.items() if k.casefold() == name.casefold()), default)


def now():
    return datetime.now(ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)).replace(microsecond=0)


def text(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(',', ':'), ensure_ascii=False)
    if isinstance(value, bool):
        return 'True' if value else 'False'
    return str(value)


def literal(value):
    result = text(value)
    return result.replace("'", '"') if result is not None else None


def owned(source, draft_id, actor):
    return MdmDraft.objects.filter(source=source, DraftId=draft_id, Userid=str(actor['id'])).exists()


def require_owner(source, draft_id, actor):
    # Human-approved deviation: native read/count/provided-ID append omitted this.
    if not owned(source, draft_id, actor):
        raise DraftDenied('draft_owner_required')


def prepare(payload):
    """Build the batch before execution, as the deployed processor does."""
    result = []
    for master in value(payload, 'draftData'):
        if int(value(master, 'masterId')) != 1:
            raise ValueError('MDM family is not delivered')
        grid = value(master, 'gridState')
        if grid is None:
            raise ValueError('GridState.ToString requires a value')
        data = value(master, 'dataMaster')
        keys = list(data[0]) if data else []
        # IsSelected is emitted by the generic legacy builder but is not a SKU
        # draft column: its native compile error must not gain persistence here.
        for alias in keys:
            if alias not in ALIASES and alias.lower() not in ('error', 'warning'):
                raise ValueError('invalid SKU draft column')
        columns = [ALIASES[k] for k in keys if k in ALIASES]
        columns += [k.title() for k in keys if k.lower() in ('error', 'warning')]
        rows = []
        for row in data:
            values = [literal(row[k]) for k in keys if k in ALIASES]
            values += [literal(row[k]) for special in ('error', 'warning') for k in keys if k.lower() == special]
            rows.append(dict(zip(columns, values)))
        result.append((literal(grid), text(value(master, 'status')), rows))
    return result


def write(source, payload, actor, *, modify=False):
    draft_id = value(payload, 'draftId')
    if modify and not owned(source, draft_id, actor):
        return dict(data=draft_id, status=304, message='Draft Not Found')
    if draft_id and not modify:
        require_owner(source, draft_id, actor)
    prepared = prepare(payload)
    new = not draft_id
    if new:
        draft_id = str(actor['id']) + now().strftime('%m%d%y%H%M%S')
    # Native header literals are not escaped. Reject unrepresentable literals;
    # do not execute caller SQL or claim arbitrary SQL-fragment emulation.
    for item in (draft_id, value(payload, 'instanceName'), value(payload, 'searchKey')):
        if item is not None and "'" in str(item):
            raise ValueError('invalid draft header SQL literal')
    if modify:
        MdmDraft.objects.filter(source=source, DraftId=draft_id).update(
            Masters=value(payload, 'instanceName'), SearchKeys=value(payload, 'searchKey'), LastModifiedDateTime=now())
        MdmDraftSku.objects.filter(source=source, Draftid=draft_id).delete()
        MdmDraftMaster.objects.filter(source=source, DraftId=draft_id).delete()
    elif new:
        MdmDraft.objects.create(source=source, DraftId=draft_id, ActionType=value(payload, 'actionType', 0),
            Masters=value(payload, 'instanceName'), SearchKeys=value(payload, 'searchKey'),
            Userid=str(actor['id']), LastModifiedDateTime=now(), CreationDateTime=now())
    for grid, status, rows in prepared:
        if new or modify:
            MdmDraftMaster.objects.create(source=source, DraftId=draft_id, MasterId=1, GridState=grid, Status=status)
            ordinal = 0
        else:
            ordinal = MdmDraftSku.objects.filter(source=source, Draftid=draft_id).aggregate(n=Max('RowId'))['n']
        for row in rows:
            ordinal = ordinal + 1 if ordinal is not None else None
            # Separate INSERT statements preserve the native partial commit
            # boundary, including NULL max(RowId) failing on an empty append.
            MdmDraftSku.objects.create(source=source, Draftid=draft_id, RowId=ordinal, **row)
    return dict(data=draft_id, status=200,
        message='Draft Updated Successfully' if modify else 'Draft Created Successfully')


def delete(source, draft_id, actor):
    if not owned(source, draft_id, actor):
        return dict(status=304, message='Draft Not Found')
    MdmDraftSku.objects.filter(source=source, Draftid=draft_id).delete()
    MdmDraftMaster.objects.filter(source=source, DraftId=draft_id).delete()
    MdmDraft.objects.filter(source=source, DraftId=draft_id).delete()
    return dict(status=200, message='Draft Deleted Successfully')


def omit_nulls(row):
    return {k: v for k, v in row.items() if v is not None}


def listing(source, actor):
    rows = []
    for draft in MdmDraft.objects.filter(source=source, Userid=str(actor['id'])):
        stamp = draft.LastModifiedDateTime
        rows.append(omit_nulls(dict(DraftId=draft.DraftId, ActionType=draft.ActionType,
            Masters=draft.Masters, userid=draft.Userid, SearchKeys=draft.SearchKeys,
            LastModifiedDateTime=stamp.astimezone(ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)).replace(tzinfo=None).isoformat() if stamp else None)))
    return rows


def count(source, draft_id, actor):
    require_owner(source, draft_id, actor)
    if not MdmDraftMaster.objects.filter(source=source, DraftId=draft_id, MasterId=1).exclude(GridState__isnull=True).exclude(GridState='').exists():
        raise ValueError('native draft count has no dynamic statement')
    return json.dumps([{'masterid': 1, 'recordCount': MdmDraftSku.objects.filter(source=source, Draftid=draft_id).count()}], separators=(',', ':'))


def details(source, draft_id, actor, payload):
    require_owner(source, draft_id, actor)
    # DraftController binds PaginationParameter directly from the request body.
    paging = payload
    page, size = int(value(paging, 'pageNumber')), int(value(paging, 'recordsPerPage'))
    rows = list(MdmDraftSku.objects.filter(source=source, Draftid=draft_id,
        RowId__gte=(page - 1) * size + 1, RowId__lte=page * size).values())
    maps = list(MdmDraftMaster.objects.filter(source=source, DraftId=draft_id, MasterId=1))
    if not maps:
        raise ValueError('native draft details has no dynamic statement')
    aliases = any(item.GridState for item in maps)
    if aliases:
        columns = {alias: name for alias, name in ALIASES.items() if FIELDS[alias]['IsDownload']}
        columns.update(error='Error', warning='Warning')
    else:
        columns = {field.name: field.name for field in MdmDraftSku._meta.fields if field.name not in ('id', 'source')}
    data = [omit_nulls({alias: row[name] for alias, name in columns.items()}) for row in rows]
    # Native UNION removes identical master-map results, not business rows.
    result = []
    for item in maps:
        if item.GridState is None or item.Status is None:
            continue  # NULL concatenation does not produce a SELECT statement.
        entry = dict(MasterId=1, Status=item.Status, GridState=item.GridState, DataMaster=data)
        if entry not in result:
            result.append(entry)
    return result
