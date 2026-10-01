"""Named operational DBM reads; calculation and command semantics stay native.

No trace, calculation, cache, publication substitution or state write. Ordinary
reads verify only the images they consume, not the whole publication checksum.
Action-bearing runs still reconstruct the complete DBM section because command
integrity is a full-state before/after contract, not a selected-table checksum.
"""
from types import SimpleNamespace

from mta.presentation import hierarchy
from mta.presentation.context import PublicationUnavailable, permission_catalogue, selected_run
from mta.presentation.selective import image_rows
from mta.runtime.temporal import command_state

GRID_TABLES = ('DBMMaster', 'Suggestions', 'NormAcceptanceTbl',
               'SKUDescriptionTbl', 'SiteDescriptionTbl', 'ReasonCodes',
               'SkuAttributeData', 'SkuLocAttributeData', 'LocationAttributeData')
HISTORY_TABLES = ('LastBatchRunTbl', 'DailyConsumption', 'SuspendHistory',
                  'NormChangeLogTbl', 'DBMMaster', 'SuspendStockType',
                  'SuspendConsumptionType', 'ReasonCodes', 'SuggestionsLog')
SCOPE_TABLES = ('SkuAttributeData', 'LocationAttributeData')


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


def dbm_context(*, history=False):
    run = selected_run()
    if run.commands.exists():
        state, _ = command_state(run, _section(run))
    else:
        tables = HISTORY_TABLES if history else GRID_TABLES
        state = {name: image_rows(run, 'closing/dbm/' + name) for name in tables}
    # History authorization is Importer-owned; grid authorization is DBM-owned.
    importer = {name: image_rows(run, 'closing/importer/' + name)
                for name in SCOPE_TABLES} if history else None
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
    return SimpleNamespace(run=run, business_date=run.business_date, dbm=state,
                           output={'ClosingState': [{'importer': importer}]} if history else {})
