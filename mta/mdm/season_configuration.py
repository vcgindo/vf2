"""The deployed master10/11/12 configuration, including native field spelling."""
import json
from pathlib import Path

CONFIG = json.loads((Path(__file__).resolve().parents[1] /
    'config/mdm_season.json').read_text(encoding='utf-8'))


def fields(master_id):
    return {r['Col_Code']: r for r in CONFIG['UI_MDMConfig'] if r['MasterId'] == master_id}


def aliases(master_id):
    return {k: r['TableField'].rstrip() for k, r in fields(master_id).items()}


def configuration(master_id, screen_type):
    mapper = next(r for r in CONFIG['MasterMapper'] if r['MasterId'] == master_id)
    flag = {'add': 'IsAdd', 'modify': 'IsModify', 'remove': 'IsRemove'}.get(screen_type)
    if flag and not mapper[flag]:
        return []
    return [dict(id=str(master_id), name=mapper['MasterName'], fields=[
        dict(displayName=r['Header'], key=k, col_Position=str(r['Col_Position']),
             visible=r['Visible'], isAdd=r['IsAdd'], isEdit=r['IsEdit'],
             isDelete=r['IsDelete'], isDownload=r['IsDownload'],
             isApplicable=r['IsApplicable'], dataType=r['DataType'])
        for k, r in fields(master_id).items()])]
