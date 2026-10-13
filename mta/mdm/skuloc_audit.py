"""Native master3 upload/decision audit statements, without report export."""
from mta.mdm.clock import database_now
from mta.runtime.mdm_supplier_models import MdmSupplierConfiguration
from mta.runtime.mdm_skuloc_models import (
    MdmSkuLocAddUploadLog, MdmSkuLocModifyUploadLog, MdmSkuLocRemoveUploadLog,
)


MODELS = {1: MdmSkuLocAddUploadLog, 2: MdmSkuLocModifyUploadLog,
          3: MdmSkuLocRemoveUploadLog}


def enabled(source):
    # This existing owner binds the shared ActivateNMSUIUploadLogs setting
    # during native initialization. Missing configuration is not disabled.
    return MdmSupplierConfiguration.objects.get(source=source).upload_log_active


def submitted(source, action, rows, actor, *, active):
    if not active:
        return
    model = MODELS[action]
    stamp = database_now()
    values = ([{'SKUCode': row['SKUCode'], 'WHCode': row['WhCode']} for row in rows]
              if action == 3 else rows)
    model.objects.bulk_create([model(source=source, **row,
        UserName=actor['name'], ActionTimeStamp=stamp, ActionId=1) for row in values])


def reviewed(source, action, rows, actor, *, active):
    if not active:
        return
    model = MODELS[action]
    location = 'WHCode' if action == 3 else 'WhCode'
    # Native EntryInLogTable emits rejection before approval. Every submitted
    # decision occurrence is retained; identical duplicate keys are not deduped.
    for status in ('4', '3'):
        stamp = database_now()
        model.objects.bulk_create([model(source=source, SKUCode=row['sc'],
            **{location: row['wc']}, UserName=actor['name'],
            ActionTimeStamp=stamp, ActionId=int(status))
            for row in rows if str(row['status']) == status])
