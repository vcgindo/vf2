"""Immutable post-BPR input-table capture with typed relational business cells."""
from django.db import connection, transaction
from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY, SCHEMA_SHA256
from mta.application.operational_inputs import PHYSICAL_TABLES
from mta.runtime.operational_source_models import OperationalInputSource, OperationalCaptureAuthorization
from mta.runtime.relational_state import save_image, load_image
from mta.runtime.validation_storage import read_input
from mta.serialization import digest, storage

# Reuse existing typed row layouts, not their working-state images. Every image
# is independently owned by this run and operational/input/<native table>.
STORAGE_BINDINGS = dict(MasterDataRaw='Importer/MasterDataRaw',
    DailyDataRaw='Intermediate/TempDailyDataRaw', SOBDataRaw='Intermediate/TempSOBDataRaw',
    MOQDataRaw1='Intermediate/TempMOQDataRaw1')


def write_input_source(run,populations):
    if transaction.get_autocommit() or run.status!='RUNNING' or run.completed_at is not None:
        raise ValueError('Input-table capture requires the live production transaction')
    profile=read_input(run,components=('profile',))['profile']
    authorization=OperationalCaptureAuthorization.objects.get(run=run)
    if (profile.get('operational_input_sources')!=INPUT_CAPTURE_POLICY
            or authorization.input_digest!=run.input_digest):
        raise ValueError('New-run processed input capture authorization required')
    if not isinstance(populations,dict) or set(populations)!=set(PHYSICAL_TABLES):
        raise ValueError('All four processed input sources required')
    if OperationalInputSource.objects.filter(run=run).exists():
        raise ValueError('Processed input source already captured')
    from mta.application.operational_input_capture import capture_input_tables
    checked=capture_input_tables(controls={'raw_master':populations['MasterDataRaw']},
        daily={'DailyDataRaw':populations['DailyDataRaw']},supplier=populations)
    images={name:save_image(run,'operational/input/'+name,None,storage(checked[name]),
                           table=STORAGE_BINDINGS[name]) for name in PHYSICAL_TABLES}
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.operational_capture_run',%s,true)",[str(run.pk)])
    source=OperationalInputSource.objects.create(run=run,policy=INPUT_CAPTURE_POLICY,
        input_digest=run.input_digest,schema_digest=SCHEMA_SHA256,rows_digest=digest(checked),images=images)
    if _rows(source)!=storage(checked):
        raise ValueError('Processed input capture readback differs')
    return source


def _rows(source):
    if (source.policy!=INPUT_CAPTURE_POLICY or source.schema_digest!=SCHEMA_SHA256
            or set(source.images)!=set(PHYSICAL_TABLES)):
        raise ValueError('Processed input capture schema/policy differs')
    for name,item in source.images.items():
        if item['image']!='operational/input/'+name or item['table']!=STORAGE_BINDINGS[name]:
            raise ValueError('Processed input source image owner differs')
    rows={name:load_image(source.run,item) for name,item in source.images.items()}
    if digest(rows)!=source.rows_digest:
        raise ValueError('Processed input source values/order differ')
    return rows


def read_input_source(run):
    if run.status!='SUCCEEDED':
        raise ValueError('Completed input-table source owner required')
    source=OperationalInputSource.objects.get(run=run)
    if source.input_digest!=run.input_digest:
        raise ValueError('Processed input source input identity differs')
    return _rows(source)
