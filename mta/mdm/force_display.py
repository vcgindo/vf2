"""Approved isolated current-display fixture; operational NMSAllItems stays empty."""
import hashlib
import json
from django.conf import settings

from django.db import connection, transaction
from mta.mdm.force_source import ARTIFACT_SHA, OWNED_DATABASE, TRIAL_SOURCE_SHA, require_installed
from mta.runtime.mdm_force_models import MdmForceDisplayOwner, MdmForceDisplayRow
from mta.runtime.mdm_skuloc_models import MdmSkuLocCurrent
from mta.serialization import digest

SOURCE_SHA = TRIAL_SOURCE_SHA
PROPOSAL_SHA = '416d31eec8e6618ef3cc57c1153cbce006116f53f82a22dfce6efbce8513c639'
AUTHORIZATION = 'call_ae59fd3f25b44635b736b243ecf48f3e:0'
FIELDS = ('SKUCode', 'WhCode', 'Norm')
HISTORY_PROPOSAL_SHA = '32f4d257abbf2b008be5f59bcacd8b1fa9cb92bced4413765c9156c6c7a7dddd'
PRESERVED_TASK = '4_20261008215131'


def history_model(source, task_id):
    """Explicit isolated history-input opt-in; ordinary native reads stay intact."""
    opt_in = getattr(settings, 'VF_MTA_FORCE_HISTORY_FIXTURE', '')
    if not opt_in or source.digest != SOURCE_SHA or task_id == PRESERVED_TASK:
        return MdmSkuLocCurrent
    if opt_in != HISTORY_PROPOSAL_SHA:
        raise ValueError('Force history fixture proposal identity differs')
    model = current_model(source)
    if model is not MdmForceDisplayRow:
        raise ValueError('Approved Force history fixture requires its display owner')
    return model


def provenance(source, rows_digest):
    return dict(schema='fresh-force-current-display-fixture-v1',
        source_digest=source.digest, artifact_sha256=ARTIFACT_SHA,
        proposal_sha256=PROPOSAL_SHA, authorization=AUTHORIZATION,
        input_path='/case/opening/importer/MasterData', rows_digest=rows_digest)


def current_model(source):
    owner = MdmForceDisplayOwner.objects.filter(source=source).first()
    if owner is None:
        return MdmSkuLocCurrent
    require_installed(source)
    rows = list(MdmForceDisplayRow.objects.filter(source=source, owner='Importer')
                .order_by('ordinal').values(*FIELDS))
    if (source.digest != SOURCE_SHA or len(rows) != 10
            or digest(rows) != owner.rows_digest
            or owner.provenance != provenance(source, owner.rows_digest)
            or digest(owner.provenance) != owner.receipt_digest
            or MdmSkuLocCurrent.objects.filter(source=source).exists()):
        raise ValueError('Approved Force current-display fixture identity differs')
    return MdmForceDisplayRow


@transaction.atomic
def install(source, raw):
    require_installed(source)
    if source.digest != SOURCE_SHA or hashlib.sha256(raw).hexdigest() != ARTIFACT_SHA:
        raise ValueError('Force current-display fixture requires the approved source and opening')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        if cursor.fetchone()[0] != OWNED_DATABASE:
            raise ValueError('Force display fixture requires its owned database')
    if (MdmForceDisplayOwner.objects.filter(source=source).exists()
            or MdmForceDisplayRow.objects.filter(source=source).exists()
            or MdmSkuLocCurrent.objects.filter(source=source).exists()):
        raise ValueError('Force display installation cannot replace any population')
    rows = [{name: row[name] for name in FIELDS} for row in
            json.loads(raw)['case']['opening']['importer']['MasterData']]
    if len(rows) != 10:
        raise ValueError('Force display fixture roster differs')
    receipt = provenance(source, digest(rows))
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.force_display_source',%s,true)", [str(source.pk)])
    MdmForceDisplayOwner.objects.create(source=source, provenance=receipt,
        receipt_digest=digest(receipt), rows_digest=digest(rows))
    MdmForceDisplayRow.objects.bulk_create([MdmForceDisplayRow(source=source,
        ordinal=i, **row) for i, row in enumerate(rows)])
    current_model(source)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.force_display_source','',true)")
    return receipt
