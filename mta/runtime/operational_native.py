"""Native operational rows owned by a side-effect attempt, never trace payloads."""
import hashlib
import json
from pathlib import Path
from django.db import models, transaction
from mta.runtime.operational_models import OperationalAttempt
from mta.serialization import digest, storage
from mta.application.operational_inputs import typed_value

_raw=(Path(__file__).resolve().parents[2]/'baseline/cohort2-native-source-schema.json').read_bytes()
if hashlib.sha256(_raw).hexdigest()!='e3bd3c715a19c78e64c287bbbe63496a77a9c325f709a74c5499b258f5acc079':
    raise ValueError('Pinned operational native schema differs')
SCHEMA=json.loads(_raw)
_alert_raw=(Path(__file__).resolve().parents[2]/'baseline/cohort2-alert-source-schema.json').read_bytes()
if hashlib.sha256(_alert_raw).hexdigest()!='c6c22f36719e39fdd3668717ccc31a0019f6feaed6780ef537d68ac837543375':
    raise ValueError('Pinned operational alert schema differs')
SCHEMA['tables'].update(json.loads(_alert_raw)['tables'])
MODELS={}


class OperationalPopulation(models.Model):
    attempt=models.ForeignKey(OperationalAttempt,on_delete=models.PROTECT)
    image=models.CharField(max_length=180)
    table=models.CharField(max_length=120)
    schema_digest=models.CharField(max_length=64)
    rows_digest=models.CharField(max_length=64)
    row_count=models.PositiveBigIntegerField()

    class Meta:
        app_label='fresh_mta'
        constraints=[models.UniqueConstraint(fields=['attempt','image'],name='op_population_image')]


def _field(column):
    kind=column['type'];options={'null':column['nullable'],'db_column':column['name']}
    if kind in ('varchar','nvarchar','char','nchar','xml'):return models.TextField(**options)
    if kind in ('int','bigint','smallint'):return models.BigIntegerField(**options)
    if kind=='bit':return models.BooleanField(**options)
    if kind in ('float','real'):return models.FloatField(**options)
    if kind in ('numeric','decimal'):
        precision,scale=map(int,column['parameters'].split(','))
        return models.DecimalField(max_digits=precision,decimal_places=scale,**options)
    if kind=='date':return models.DateField(**options)
    if kind in ('datetime','datetime2'):return models.DateTimeField(**options)
    raise ValueError('Unsupported operational SQL column type:'+kind)


def _field_name(table, ordinal):
    # Migration 0083 shipped the SKU log without these three native columns.
    # Preserve its existing field identities while restoring native export order.
    if table == 'Importer/UIUploadLogNMSSKUs':
        if 2 <= ordinal <= 4:
            return 'field_' + str(ordinal + 23)
        if ordinal >= 5:
            return 'field_' + str(ordinal - 3)
    return 'field_' + str(ordinal)


for _table,_columns in SCHEMA['tables'].items():
    # Raw input exports already have immutable typed day owners. Only newly
    # produced reports/logs receive additional physical operational rows.
    if _table.split('/')[-1] in ('MasterDataRaw','DailyDataRaw','SOBDataRaw','MOQDataRaw1'):
        continue
    _token=hashlib.sha256(_table.encode()).hexdigest()[:10]
    _attrs={'__module__':__name__,
        'attempt':models.ForeignKey(OperationalAttempt,on_delete=models.PROTECT),
        'image':models.CharField(max_length=180),'ordinal':models.PositiveBigIntegerField()}
    _attrs.update({_field_name(_table,i):_field(c) for i,c in enumerate(_columns)})
    _attrs['Meta']=type('Meta',(),dict(app_label='fresh_mta',db_table='op_native_'+_token,
        constraints=[models.UniqueConstraint(fields=['attempt','image','ordinal'],name='op_native_'+_token+'_ord')]))
    _name='OperationalNative'+_table.replace('/','')
    MODELS[_table]=type(_name,(models.Model,),_attrs)
    globals()[_name]=MODELS[_table]


def _wire(row,columns):
    from datetime import datetime, timezone
    result={}
    for column,value in zip(columns,row,strict=True):
        if isinstance(value,datetime) and value.tzinfo is not None:
            value=value.astimezone(timezone.utc).replace(tzinfo=None)
        result[column['name']]=storage(value)
    return result


def read_population(attempt,image):
    receipt=OperationalPopulation.objects.get(attempt=attempt,image=image)
    columns=SCHEMA['tables'][receipt.table]
    if receipt.schema_digest!=digest(columns):raise ValueError('Operational schema changed')
    values=MODELS[receipt.table].objects.filter(attempt=attempt,image=image).order_by('ordinal')
    fields=[_field_name(receipt.table,i) for i in range(len(columns))]
    rows=[]
    for expected_ordinal,row in enumerate(values.values_list('ordinal',*fields).iterator(chunk_size=200)):
        if row[0]!=expected_ordinal:
            raise ValueError('Operational typed population ordinal differs')
        rows.append(_wire(row[1:],columns))
    if len(rows)!=receipt.row_count or digest(rows)!=receipt.rows_digest:
        raise ValueError('Operational typed population changed')
    return rows


@transaction.atomic
def save_population(attempt,image,table,rows):
    from datetime import timezone
    owner=OperationalAttempt.objects.select_for_update().get(pk=attempt.pk)
    from mta.runtime.operational_lease import require_attempt_lease
    require_attempt_lease(owner)
    if owner.status!='RUNNING':raise ValueError('Operational population needs a running owner')
    if OperationalPopulation.objects.filter(attempt=attempt,image=image).exists():
        raise ValueError('Operational population already persisted')
    columns=SCHEMA['tables'][table];names={c['name'] for c in columns};instances=[];expected=[]
    for ordinal,row in enumerate(rows):
        if set(row)!=names:raise ValueError('Operational native column roster differs:'+table)
        fields={}
        for i,column in enumerate(columns):
            value=typed_value(row[column['name']],column,reserve_null_token=False)
            if value is not None and column['type'] in ('datetime','datetime2'):
                value=value.replace(tzinfo=timezone.utc)
            fields[_field_name(table,i)]=value
        expected.append(_wire(fields.values(),columns))
        instances.append(MODELS[table](attempt=attempt,image=image,ordinal=ordinal,**fields))
    MODELS[table].objects.bulk_create(instances,batch_size=200)
    receipt=OperationalPopulation.objects.create(attempt=attempt,image=image,table=table,
        schema_digest=digest(columns),rows_digest=digest(expected),row_count=len(expected))
    if read_population(attempt,image)!=expected:raise ValueError('Operational native readback mismatch')
    require_attempt_lease(owner)
    return receipt
