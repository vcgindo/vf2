"""Pinned shared configuration for ADD-only phase-control masters 7, 8 and 9."""
import json
from pathlib import Path


CONFIG = json.loads((Path(__file__).resolve().parents[1] /
                     'config/mdm_phase_controls.json').read_text(encoding='utf-8'))
MAPPERS = {row['MasterId']: row for row in CONFIG['MasterMapper']}
FIELDS = {master_id: {row['Col_Code']: row for row in CONFIG['UI_MDMConfig']
                      if row['MasterId'] == master_id}
          for master_id in MAPPERS}
ALIASES = {master_id: {alias: row['TableField']
                       for alias, row in fields.items()}
           for master_id, fields in FIELDS.items()}
# DraftAddPIPOMaster is shared, but each master writes only its configured
# aliases. All IsDownload flags are false, so draft reload remains the native
# raw projection: RowId, DraftId, Error, SKUCode, WhCode, PhaseInSKUCode,
# TargetNorm and Warning.
DRAFT_ALIASES = {master_id: dict(aliases)
                 for master_id, aliases in ALIASES.items()}


def configuration(master_id, screen_type):
    mapper = MAPPERS[int(master_id)]
    flag = {'add': 'IsAdd', 'modify': 'IsModify', 'remove': 'IsRemove'}.get(screen_type)
    if flag and not mapper[flag]:
        return []
    fields = [dict(displayName=row['Header'], key=alias,
        col_Position=str(row['Col_Position']), visible=row['Visible'],
        isAdd=row['IsAdd'], isEdit=row['IsEdit'], isDelete=row['IsDelete'],
        isDownload=row['IsDownload'], isApplicable=row['IsApplicable'],
        dataType=row['DataType']) for alias, row in FIELDS[int(master_id)].items()]
    return [dict(id=str(mapper['MasterId']), name=mapper['MasterName'], fields=fields)]
