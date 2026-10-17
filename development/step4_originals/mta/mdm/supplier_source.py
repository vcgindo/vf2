"""Explicit installation of supplier application owners; no report fallback."""
import hashlib
import json
import math
from pathlib import Path

from django.db import connection, transaction
from mta.mdm.source import DLL
from mta.mdm.supplier_input import FORMATS
from mta.runtime.mdm_models import MdmSource, MdmFamilySource
from mta.runtime.mdm_supplier_models import (MdmSupplierConfiguration,
                                            MdmSobRaw, MdmMoqRaw1, MdmMoqRaw2)
from mta.serialization import digest

SCHEMA = 'fresh-mdm-supplier-source-v1'
CONFIGURATION = {name: hashlib.sha256((Path(__file__).resolve().parents[1] /
    ('config/mdm_' + name + '.json')).read_bytes()).hexdigest() for name in ('sob', 'moq')}
MODELS = {'SOBDataRaw': MdmSobRaw, 'MOQDataRaw1': MdmMoqRaw1, 'MOQDataRaw2': MdmMoqRaw2}


def require_installed(source, master_id):
    from mta.presentation.context import PublicationUnavailable
    try:
        config = MdmSupplierConfiguration.objects.get(source=source)
        family = MdmFamilySource.objects.get(source=source, master_id=int(master_id))
    except (MdmSupplierConfiguration.DoesNotExist, MdmFamilySource.DoesNotExist):
        raise PublicationUnavailable('mdm_supplier_family_not_installed') from None
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    if source.receipt.get('schema') == SOURCE_SCHEMA:
        from mta.mdm.production_families import require_owner
        return require_owner(source, config, 'supplier')
    if (family.receipt.get('schema') != SCHEMA or family.receipt.get('dll_sha256') != DLL
            or source.dll_digest != DLL
            or family.receipt.get('configuration') != CONFIGURATION
            or family.receipt.get('moq_format') != config.moq_format
            or family.receipt.get('upload_log_active') != config.upload_log_active
            or family.digest != digest(family.receipt)
            or family.receipt.get('installation_digest') != config.receipt_digest):
        raise ValueError('Supplier application installation identity differs')
    from mta.mdm.integration_source import DAILY_OWNER_SCHEMA, verify_owner_anchor
    if config.provenance.get('schema') == DAILY_OWNER_SCHEMA:
        verify_owner_anchor(source, config.provenance)
        if (config.provenance.get('family') != 'supplier'
                or family.receipt.get('closing_binding_digest') != digest(config.provenance)):
            raise ValueError('Supplier accepted closing provenance differs')
    return config


@transaction.atomic
def bind(source, run):
    """Install the three typed raw bags from this source's actual daily closing."""
    from mta.mdm.integration_source import accepted_closing
    from mta.serialization import storage
    source, closing, p = accepted_closing(source, run, (4, 5))
    # Complete daily production persists these raw owners, not merely processed SOB/MOQ.
    raw = {name: closing['complete'][name] for name in MODELS}
    settings = closing['importer_settings']
    def setting(name):
        values = [r['Value'] for r in settings if r['Parameter'] == name]
        if len(values) != 1:
            raise ValueError('Supplier accepted closing requires one explicit ' + name)
        return values[0]
    moq_format, active = setting('NMSMOQInputDataFormat'), setting('ActivateNMSUIUploadLogs')
    if str(active) not in ('0', '1'):
        raise ValueError('Supplier accepted closing upload log flag differs')
    p.update(family='supplier', raw_digests={name: digest(rows) for name, rows in raw.items()})
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.supplier_closing_bind',%s,true)", [f'{source.pk}:{run.pk}'])
    config = install(source, raw, moq_format=moq_format, upload_log_active=str(active) == '1', provenance=p)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.supplier_closing_bind','',true)")
    for name, model in MODELS.items():
        fields = [f.name for f in model._meta.fields if f.name not in ('id', 'source', 'ordinal')]
        actual = list(model.objects.filter(source=source).order_by('ordinal').values(*fields))
        if storage(actual) != storage(raw[name]):
            raise ValueError('Supplier accepted closing typed readback differs: ' + name)
    return config


@transaction.atomic
def install(source, raw, *, moq_format, upload_log_active, provenance):
    source = MdmSource.objects.select_for_update().get(pk=source.pk)
    from mta.mdm.integration_source import require_unsealed
    require_unsealed(source)
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    if MdmDailyInputCapture.objects.filter(source=source, status='CAPTURED',
                                           retries__isnull=True).exists():
        raise ValueError('Supplier installation cannot change a pending frozen capture roster')
    if source.dll_digest != DLL or moq_format not in FORMATS or type(upload_log_active) is not bool:
        raise ValueError('Explicit native supplier source/configuration required')
    if not isinstance(provenance, dict) or not provenance or len(json.dumps(provenance)) > 16384:
        raise ValueError('Bounded explicit supplier provenance required')
    if set(raw) != set(MODELS):
        raise ValueError('All three explicit raw supplier bags required')
    if (MdmSupplierConfiguration.objects.filter(source=source).exists()
            or MdmFamilySource.objects.filter(source=source, master_id__in=(4, 5)).exists()
            or any(model.objects.filter(source=source).exists() for model in MODELS.values())):
        raise ValueError('Supplier owners already installed; reset is prohibited')
    prepared = {}
    for name, model in MODELS.items():
        fields = [f for f in model._meta.fields if f.name not in ('id', 'source', 'ordinal')]
        expected = {f.name for f in fields}
        prepared[name] = []
        for ordinal, row in enumerate(raw[name], 1):
            if set(row) != expected:
                raise ValueError('Supplier raw columns differ: ' + name)
            values = {}
            for field in fields:
                value = row[field.name]
                if value is not None:
                    kind = field.get_internal_type()
                    if kind == 'FloatField':
                        if type(value) not in (int, float) or not math.isfinite(value):
                            raise ValueError('Native float53 required')
                        value = float(value)
                    elif kind == 'IntegerField':
                        if type(value) is not int or not -2147483648 <= value <= 2147483647:
                            raise ValueError('Native int32 required')
                    elif not isinstance(value, str) or len(value) > field.max_length:
                        raise ValueError('Native bounded text required')
                values[field.name] = value
            prepared[name].append(model(source=source, ordinal=ordinal, **values))
    installation = digest(dict(raw=raw, moq_format=moq_format,
        upload_log_active=upload_log_active, provenance=provenance))
    config = MdmSupplierConfiguration.objects.create(source=source, moq_format=moq_format,
        upload_log_active=upload_log_active, provenance=provenance, receipt_digest=installation)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.mdm_supplier_bootstrap',%s,true)", [str(source.pk)])
    for name, model in MODELS.items():
        model.objects.bulk_create(prepared[name])
    for master_id in (4, 5):
        receipt = dict(schema=SCHEMA, dll_sha256=DLL, configuration=CONFIGURATION,
                       installation_digest=installation, master_id=master_id,
                       moq_format=moq_format, upload_log_active=upload_log_active)
        from mta.mdm.integration_source import DAILY_OWNER_SCHEMA
        if provenance.get('schema') == DAILY_OWNER_SCHEMA:
            receipt['closing_binding_digest'] = digest(provenance)
        MdmFamilySource.objects.create(source=source, master_id=master_id,
                                       digest=digest(receipt), receipt=receipt)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.mdm_supplier_bootstrap','',true)")
    return config
