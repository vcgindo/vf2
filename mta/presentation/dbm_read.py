"""Named operational DBM reads; calculation and command semantics stay native.

No trace, calculation, cache, publication substitution or state write. Ordinary
reads verify only the images they consume, not the whole publication checksum.
Action-bearing runs still reconstruct the complete DBM section because command
integrity is a full-state before/after contract, not a selected-table checksum.
"""
from types import SimpleNamespace
from datetime import date,timedelta
from django.db import connection

from mta.presentation import hierarchy
from mta.presentation.context import PublicationUnavailable, permission_catalogue, selected_run
from mta.presentation.selective import image_rows,image_metadata,image_query
from mta.runtime.relational_state import quote,wire_value
from mta.runtime.temporal import command_state

GRID_TABLES = ('DBMMaster', 'Suggestions', 'NormAcceptanceTbl',
               'SKUDescriptionTbl', 'SiteDescriptionTbl', 'ReasonCodes',
               'SkuAttributeData', 'SkuLocAttributeData', 'LocationAttributeData')
HISTORY_TABLES = ('LastBatchRunTbl', 'DailyConsumption', 'SuspendHistory',
                  'NormChangeLogTbl', 'DBMMaster', 'SuspendStockType',
                  'SuspendConsumptionType', 'ReasonCodes', 'SuggestionsLog')
SCOPE_TABLES = ('SkuAttributeData', 'LocationAttributeData')


def _selected_rows(run,path,selected,*,cutoff=None,date_field=None,metadata=None):
    """Filter immutable native rows before transfer, retaining physical order."""
    item=metadata if metadata is not None else image_metadata(run,path)
    if not item['count']:return []
    fields={name:(column,kind) for name,column,kind in item['fields']}
    where=[];params=[]
    for name,value in selected.items():
        column,kind=fields[name]
        # The graph's Python tuple comparison is raw and type-sensitive;
        # numeric codes must not be coerced to a matching request string.
        if kind!='str':return []
        where.append('S.'+quote(column)+' COLLATE "C"=%s COLLATE "C"')
        params.append(value)
    if cutoff is not None and fields[date_field][1]=='str':
        column=quote(fields[date_field][0])
        # Preserve the projection's existing error for a selected NULL date;
        # SQL must not silently turn an invalid value into an excluded row.
        where.append('(S.'+column+' IS NULL OR S.'+column+'>=%s)')
        params.append(cutoff)
    query,source_params=image_query(run,path,metadata=item)
    projection=','.join('S.'+quote(column) for column,kind in fields.values())
    rows=[]
    with connection.cursor() as cursor:
        cursor.execute('SELECT '+projection+' FROM ('+query+') S WHERE '+
            ' AND '.join(where)+' ORDER BY S.vf_ordinal',source_params+params)
        while batch:=cursor.fetchmany(500):
            rows.extend({name:wire_value(value,kind) for (name,(column,kind)),value in zip(fields.items(),record)}
                        for record in batch)
    return rows


def _history_pair(run,pair):
    sku,location=pair
    state={'LastBatchRunTbl':image_rows(run,'closing/dbm/LastBatchRunTbl'),
           'ReasonCodes':image_rows(run,'closing/dbm/ReasonCodes')}
    cutoff=(date.fromisoformat(state['LastBatchRunTbl'][0]['LastRunDate'][:10])-timedelta(days=90)).isoformat()
    windows={'DailyConsumption':'ReportDate','SuspendHistory':'ReportDate','SuggestionsLog':'SuggestionDate'}
    for name in HISTORY_TABLES:
        if name in state:continue
        path='closing/dbm/'+name
        item=image_metadata(run,path)
        fields={f[0] for f in item['fields']}
        location_field=next((field for field in ('WhCode','WHCode','LocCode') if field in fields),None)
        if not item['count']:
            state[name]=[]
            continue
        if location_field is None:
            raise PublicationUnavailable('daily_graph_location_column_missing:'+name)
        state[name]=_selected_rows(run,path,{'SKUCode':sku,location_field:location},
            cutoff=cutoff if name in windows else None,date_field=windows.get(name),metadata=item)
    importer={name:_selected_rows(run,'closing/importer/'+name,
        {'SKUCode':sku} if name=='SkuAttributeData' else {'WHCode':location}) for name in SCOPE_TABLES}
    return state,importer


def _section(run):
    # Same manifest resolution as the production reader, limited to DBM.
    def resolve(node):
        if 'image' in node:
            return image_rows(run, node['image'])
        if 'metadata' in node:
            return node['metadata']
        if 'scratch_kind' in node:
            records = [(name, resolve(value)) for name, value in node['items']]
            return dict(records) if node['scratch_kind'] == 'dict' else [
                {'table': name, 'rows': rows} for name, rows in records]
        return {name: resolve(value) for name, value in node['tables'].items()}
    return resolve(run.production_manifest['closing']['dbm'])


def dbm_context(*, history=False, pair=None, payload=None):
    run = selected_run()
    commands=run.commands.exists()
    selective=history and pair is not None and not commands
    if selective:
        if not isinstance(pair,(tuple,list)) or len(pair)!=2 or any(not isinstance(v,str) for v in pair):
            raise ValueError('SKUCode_and_WHCode_required')
        state,importer=_history_pair(run,pair)
    elif commands:
        state, _ = command_state(run, _section(run))
    else:
        tables = HISTORY_TABLES if history else GRID_TABLES
        state = {name: image_rows(run, 'closing/dbm/' + name) for name in tables}
    if not selective:
        importer = {name: image_rows(run, 'closing/importer/' + name) for name in SCOPE_TABLES} if history else None
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            catalogue = permission_catalogue()
            if history:
                importer = hierarchy.project_attributes(importer, catalogue, manifest)
            else:
                state = hierarchy.project_attributes(state, catalogue, manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    return SimpleNamespace(run=run, business_date=run.business_date, dbm=state, output={'ClosingState': [{'importer': importer}]} if history else {})
