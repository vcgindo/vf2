"""PostBTR's immutable source is the projection prepared before finalization.

Reference the closing cut only after proving its projected rows reproduce that
source. The publication receipt still owns the file and its original digest.
"""
from django.db import connection

from mta.row_sequences import RecordRows
from mta.runtime import rationing_reader as history
from mta.runtime import runtime_report_stage_storage as images
from mta.runtime.runtime_report_sources import scalar


FORMAT = 'postbtr-rationing-cut-v1'
FIELDS = ('ParentWhCode', 'ParentWhName', 'SKUCode', 'SKUName', 'WhCode', 'WhName',
          'IsNormed', 'Req', 'ParentNorm', 'RationedReq', 'SupplierDispatchReq',
          'DispatchPen', 'DispatchColor', 'Dispatch', 'ReportDate', 'Stock', 'GIT')


def _reference(cut, descriptor):
    return dict(format=FORMAT, cut_id=str(cut.identity), root_digest=cut.root_digest,
                projection_digest=descriptor['digest'])


def _project(cut, fields):
    types = dict(images.LOGICAL[history.TABLE])
    if not fields or len(set(fields)) != len(fields) or not set(fields) <= types.keys():
        raise ValueError('Invalid PostBTR history projection')
    def records():
        for _, row in history.iter_occurrences(cut, names=fields if cut.body['fields'] else ()):
            yield {name: scalar(row[name], types[name]) for name in fields}
    return RecordRows(cut.body['count'], records)


def _pending_cut(run, work, metadata):
    from mta.runtime.state_cut_models import OperationalStateCut
    if not connection.in_atomic_block or work.placement != 'PostBTR':
        raise ValueError('PostBTR reference requires the active completion transaction')
    with connection.cursor() as cursor:
        cursor.execute("""SELECT mta.runtime_report_write_owner(%s)
            AND current_setting('fresh.runtime_report_candidate',true)=%s
            AND (current_setting('fresh.mdm_consuming_run',true)=%s OR mta.pending_day_final(%s))""",
            [run.pk, work.candidate_id, str(run.pk), run.pk])
        if cursor.fetchone() != (True,):
            raise ValueError('PostBTR reference requires its existing completion owner')
    row = OperationalStateCut.objects.values(*history.CUT_FIELDS).get(pk=metadata['cut_id'],
        run=run, run__status='RUNNING', position__gt=0, input_digest=run.input_digest,
        settings_digest=work.owner['profile_digest'])
    cut = history._sealed_header(row)
    if history.image_metadata(cut) != metadata:
        raise ValueError('PostBTR closing image differs from its sealed cut')
    return cut


def persist(run, work, metadata):
    cut = _pending_cut(run, work, metadata)
    manifest = images.validate_images(work.source_manifest, candidate_id=work.candidate_id,
                                      placement=work.placement)
    expected = manifest['images']
    if expected.keys() != work.sources.keys() or history.TABLE not in expected:
        raise ValueError('Prepared PostBTR source roster differs')
    descriptor = expected[history.TABLE]
    if images.describe(work.candidate_id, history.TABLE, _project(cut, FIELDS))[0] != descriptor:
        raise ValueError('PostBTR closing projection differs from the prepared source')
    # Validate every prepared bag before the first write. Once the prepared
    # history and independent cut both match, the receipt needs only the cut.
    for logical, rows in work.sources.items():
        if images.describe(work.candidate_id, logical, rows)[0] != expected[logical]:
            raise ValueError('PostBTR prepared source changed: ' + logical)
    for logical, rows in work.sources.items():
        if logical != history.TABLE and images.write(run, work.candidate_id, logical, rows) != expected[logical]:
            raise ValueError('Persisted report stage differs: ' + logical)
    return manifest, _reference(cut, descriptor)


def read_sources(run, publication, *, fields):
    """Consume the authenticated publication selected by the download owner."""
    authority = publication.metadata['authority']
    manifest = authority['images']
    options = dict(candidate_id=str(publication.pk), placement=publication.placement)
    if publication.run_id != run.pk:
        raise ValueError('Foreign report placement')
    if 'rationing_source' not in authority:
        return images.read(run, manifest, fields=fields, **options)
    images.validate_images(manifest, **options)
    descriptor = manifest['images'][history.TABLE]
    cut = history.require_image(run, run.production_manifest['images'][history.IMAGE])
    if (publication.placement != 'PostBTR' or authority['rationing_source'] != _reference(cut, descriptor)
            or descriptor['count'] != cut.body['count']
            or [field[0] for field in descriptor['fields']] != (list(FIELDS) if descriptor['count'] else [])):
        raise ValueError('PostBTR history reference differs')
    remaining = {name: roster for name, roster in fields.items() if name != history.TABLE}
    sources = images.read(run, manifest, fields=remaining, **options)
    if history.TABLE in fields:
        requested = fields[history.TABLE]
        if descriptor['count'] and not set(requested) <= set(FIELDS):
            raise ValueError('Column absent from prepared PostBTR history')
        sources[history.TABLE] = _project(cut, requested)
    return sources
