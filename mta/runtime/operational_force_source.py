"""Pre-clear force-alert inputs, committed with their owning calculation only."""
from django.db import connection, transaction
from mta.runtime.operational_source_models import OperationalForceSource, OperationalCaptureAuthorization
from mta.runtime.relational_state import save_image, load_image
from mta.runtime.validation_storage import read_input
from mta.serialization import digest, storage
from mta.application.timeline_controls import FORCE_CAPTURE_POLICY

BINDINGS = dict(ForceNormChange='Importer/ForceNormChange', DBMMaster='DBM/DBMMaster',
                MasterDataRaw='Importer/MasterDataRaw')


def _validate(populations):
    if not isinstance(populations, dict) or set(populations) != set(BINDINGS):
        raise ValueError('All three pre-clear force sources required')
    for name, rows in populations.items():
        if not isinstance(rows, list):
            raise ValueError('Explicit force source populations required')
        required = ({'skucode', 'whcode', 'newnorm', 'approved', 'requestedby'}
                    if name == 'ForceNormChange' else {'skucode', 'whcode', 'norm'})
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('Force source row mapping required')
            fields = {field.casefold() for field in row}
            if len(fields) != len(row) or not required <= fields:
                raise ValueError('Force source required fields absent or repeated: '+name)


def write_force_source(run, populations):
    if transaction.get_autocommit() or run.status != 'RUNNING' or run.completed_at is not None:
        raise ValueError('Force source requires the live production transaction')
    profile = read_input(run, components=('profile',))['profile']
    authorization = OperationalCaptureAuthorization.objects.get(run=run)
    if (profile.get('operational_force_sources') != FORCE_CAPTURE_POLICY
            or authorization.input_digest != run.input_digest):
        raise ValueError('Explicit new-run force capture authorization required')
    _validate(populations)
    if OperationalForceSource.objects.filter(run=run).exists():
        raise ValueError('Force source already captured')
    checked = storage(populations)
    images = {name: save_image(run, 'operational/force/'+name, None, checked[name], table=table)
              for name, table in BINDINGS.items()}
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.operational_capture_run',%s,true)", [str(run.pk)])
    source = OperationalForceSource.objects.create(run=run, policy=FORCE_CAPTURE_POLICY,
        input_digest=run.input_digest, rows_digest=digest(checked), images=images)
    if _rows(source) != checked:
        raise ValueError('Force source typed readback differs')
    return source


def _rows(source):
    if source.policy != FORCE_CAPTURE_POLICY or set(source.images) != set(BINDINGS):
        raise ValueError('Force source policy/roster differs')
    for name, item in source.images.items():
        if item['image'] != 'operational/force/'+name or item['table'] != BINDINGS[name]:
            raise ValueError('Force source image ownership differs')
    rows = {name: load_image(source.run, item) for name, item in source.images.items()}
    _validate(rows)
    if digest(rows) != source.rows_digest:
        raise ValueError('Force source values/order differ')
    return rows


def read_force_source(run):
    if run.status != 'SUCCEEDED':
        raise ValueError('Completed force source owner required')
    source = OperationalForceSource.objects.get(run=run)
    if source.input_digest != run.input_digest:
        raise ValueError('Force source input identity differs')
    return _rows(source)
