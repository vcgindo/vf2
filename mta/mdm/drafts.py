"""Owned SKU drafts, preserving deployed text rows and statement boundaries."""
from datetime import datetime
from zoneinfo import ZoneInfo
import json

from django.conf import settings
from django.db.models import Max
from mta.runtime.mdm_models import MdmDraft, MdmDraftMaster, MdmDraftSku
from mta.mdm import families


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
        master_id = int(value(master, 'masterId'))
        config = families.module(master_id)
        aliases = getattr(config, 'DRAFT_ALIASES', config.ALIASES)
        grid = value(master, 'gridState')
        if grid is None:
            raise ValueError('GridState.ToString requires a value')
        data = value(master, 'dataMaster')
        keys = list(data[0]) if data else []
        # IsSelected is emitted by the generic legacy builder but is not a SKU
        # draft column: its native compile error must not gain persistence here.
        for alias in keys:
            if alias not in aliases and alias.lower() not in ('error', 'warning'):
                raise ValueError('invalid draft column')
        columns = [aliases[k] for k in keys if k in aliases]
        columns += [k.title() for k in keys if k.lower() in ('error', 'warning')]
        rows = []
        for row in data:
            values = [literal(row[k]) for k in keys if k in aliases]
            values += [literal(row[k]) for special in ('error', 'warning') for k in keys if k.lower() == special]
            rows.append(dict(zip(columns, values)))
        if master_id == 6:
            # DraftPIPOMaster has native int/date columns, unlike text-only drafts.
            for row in rows:
                for column in ('OriginalNorm', 'CurrentNorm', 'PhaseInCurrNorm', 'PhaseInTargetNorm'):
                    if row.get(column) is not None:
                        number = int(row[column].strip() or '0')
                        if not -2147483648 <= number <= 2147483647:
                            raise ValueError('native draft int32 overflow')
                        row[column] = number
                for column in ('LastNormChangeDate', 'PhaseOutStartDate'):
                    if row.get(column) is not None:
                        row[column] = datetime.fromisoformat(row[column].strip() or '1900-01-01').date()
        result.append((master_id, literal(grid), text(value(master, 'status')), rows))
    return result


def write(source, payload, actor, *, modify=False):
    draft_id = value(payload, 'draftId')
    if modify and not owned(source, draft_id, actor):
        return dict(data=draft_id, status=304, message='Draft Not Found')
    if draft_id and not modify:
        require_owner(source, draft_id, actor)
    prepared = prepare(payload)
    for master_id, *_ in prepared:
        families.require_installed(source, master_id)
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
        delete_rows(source, draft_id)
        MdmDraftMaster.objects.filter(source=source, DraftId=draft_id).delete()
    elif new:
        MdmDraft.objects.create(source=source, DraftId=draft_id, ActionType=value(payload, 'actionType', 0),
            Masters=value(payload, 'instanceName'), SearchKeys=value(payload, 'searchKey'),
            Userid=str(actor['id']), LastModifiedDateTime=now(), CreationDateTime=now())
    for master_id, grid, status, rows in prepared:
        model, id_field = families.draft_model(master_id)
        selected = dict(source=source, **{id_field: draft_id})
        if new or modify:
            MdmDraftMaster.objects.create(source=source, DraftId=draft_id, MasterId=master_id, GridState=grid, Status=status)
            ordinal = 0
        else:
            ordinal = model.objects.filter(**selected).aggregate(n=Max('RowId'))['n']
        for row in rows:
            ordinal = ordinal + 1 if ordinal is not None else None
            # Separate INSERT statements preserve the native partial commit
            # boundary, including NULL max(RowId) failing on an empty append.
            model.objects.create(**selected, RowId=ordinal, **row)
    return dict(data=draft_id, status=200,
        message='Draft Updated Successfully' if modify else 'Draft Created Successfully')


def delete_rows(source, draft_id):
    for master_id in MdmDraftMaster.objects.filter(source=source, DraftId=draft_id).values_list('MasterId', flat=True).distinct():
        model, id_field = families.draft_model(master_id)
        model.objects.filter(source=source, **{id_field: draft_id}).delete()


def delete(source, draft_id, actor):
    if not owned(source, draft_id, actor):
        return dict(status=304, message='Draft Not Found')
    delete_rows(source, draft_id)
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
    maps = list(MdmDraftMaster.objects.filter(source=source, DraftId=draft_id).exclude(GridState__isnull=True).exclude(GridState=''))
    if not maps:
        raise ValueError('native draft count has no dynamic statement')
    ids = {item.MasterId for item in maps}
    if len(ids) != 1:
        # Native assigns (rather than appends) a SELECT variable without ORDER
        # BY. Do not invent which family wins a mixed-family count.
        raise ValueError('native mixed-family draft count is incomparable')
    master_id = ids.pop()
    model, id_field = families.draft_model(master_id)
    return json.dumps([{'masterid': master_id, 'recordCount': model.objects.filter(source=source, **{id_field: draft_id}).count()}], separators=(',', ':'))


def details(source, draft_id, actor, payload):
    require_owner(source, draft_id, actor)
    # DraftController binds PaginationParameter directly from the request body.
    paging = payload
    page, size = int(value(paging, 'pageNumber')), int(value(paging, 'recordsPerPage'))
    maps = list(MdmDraftMaster.objects.filter(source=source, DraftId=draft_id))
    if not maps:
        raise ValueError('native draft details has no dynamic statement')
    aliased_ids = {item.MasterId for item in maps if item.GridState and
                   any(r['IsDownload'] for r in families.module(item.MasterId).FIELDS.values())}
    if len(aliased_ids) > 1:
        # IL23138 concatenates fields across families into one projection and
        # leaves @MASTERID as an unordered last assignment. Keep it unqualified.
        raise ValueError('native mixed-family draft projection is incomparable')
    # Native UNION removes identical master-map results, not business rows.
    result = []
    for item in maps:
        if item.GridState is None or item.Status is None:
            continue  # NULL concatenation does not produce a SELECT statement.
        model, id_field = families.draft_model(item.MasterId)
        rows = list(model.objects.filter(source=source, **{id_field: draft_id},
            RowId__gte=(page - 1) * size + 1, RowId__lte=page * size).values())
        if item.MasterId in aliased_ids:
            config = families.module(item.MasterId)
            aliases = getattr(config, 'DRAFT_ALIASES', config.ALIASES)
            columns = {alias: name for alias, name in aliases.items()
                       if alias in config.FIELDS and config.FIELDS[alias]['IsDownload']}
            if item.MasterId in (6, 10):
                columns['IsSelected'] = 'IsSelected'
            columns.update(error='Error', warning='Warning')
        else:
            columns = {field.name: field.name for field in model._meta.fields if field.name not in ('id', 'source')}
        data = [omit_nulls({alias: row[name] for alias, name in columns.items()}) for row in rows]
        entry = dict(MasterId=item.MasterId, Status=item.Status, GridState=item.GridState, DataMaster=data)
        if entry not in result:
            result.append(entry)
    return result
