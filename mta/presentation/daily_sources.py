"""Publish missing narrow sources while their owning daily outputs are available.

Existing closing/history images remain in the original production manifest. This
receipt adds source-stage metadata without changing the F2 output reconstruction.
No receipt is synthesized for absent logistics, remarks or BOR producers.
"""
import inspect
import json
from datetime import datetime
from django.db import transaction
from mta.runtime.models import DailySourceReceipt, DailyColorSequence
from mta.runtime.relational_state import save_image, load_image
from mta.serialization import digest, storage
from mta.presentation.request_scope import once_per_request

COLOR_PATH = 'metadata/bpr/ColorSequence'
# Exact v5 writer observed on the retained 9bc51168 runtime before this change.
# Historical receipts remain immutable; this is not recomputed from new code.
RETAINED_V5_RECIPE = '4e110600f15a7dcf36beb191261961cbdef641c0514b5a1d89ecc4164ec71cab'
# Authenticated c21850c8 native package; both retained Full predecessors use it.
# The corrected writer publishes accepted scoped histories without recollection.
RETAINED_V6_RECIPE = '06126733256006b008a2b11b0b9e7bfefaecef56e68cd395f5d0f7474eb15b59'
# Exact 5cb02c29 producer, qualified before the action-admission change.
# Its only changed dependency passes the stored remark recipe to the existing
# binder. Source rows, fields, ordering and immutable receipt identities agree.
RETAINED_ACTION_ADMISSION_RECIPE = '2b7c330b6c043f1f73b23df3f56a2a2da8b9378eff36fd2f711cb4bf8b6ce720'


def recipe_digest():
    from mta.presentation import terminal_scoped_remarks
    from mta.presentation.daily_transit import recipe_digest as transit_recipe
    from mta.presentation.daily_opening_sob import recipe_digest as sob_recipe
    from mta.presentation.production_reports import recipe_digest as report_recipe
    from mta.runtime.bpr_history_completion import recipe_digest as completion_recipe
    return digest(dict(version=6, writer=inspect.getsource(write_sources),
                       scoped_terminal_remarks=inspect.getsource(terminal_scoped_remarks),
                       bpr_history=completion_recipe(),
                       transit_factor=inspect.getsource(_transit_factor), sob=sob_recipe(),
                       transit=transit_recipe(), reports=report_recipe()))


def _transit_factor(run, current_settings):
    """Use the captured Importer owner, not an optional DBM rule projection."""
    from mta.runtime.input_reader import read_input
    from mta.domain.complete_daily_scalars import ascii_equal
    from mta.domain.dbm_conditional import validate_settings_rows
    profile = read_input(run, components=('profile',))['profile']
    delivery = profile.get('delivery', {})
    settings_rows = delivery.get('btr_history', {}).get('importer_vf_settings')
    current = [row['Value'] for row in current_settings if row['Parameter'] == 'SuperDelayFactor']
    if settings_rows is None:
        if len(current) != 1:
            raise ValueError('Exactly one current SuperDelayFactor required')
        return current[0]
    settings_rows = list(settings_rows)
    validate_settings_rows(settings_rows)
    factors = [row for row in settings_rows if ascii_equal(row['Parameter'], 'SuperDelayFactor')]
    if len(factors) != 1:
        raise ValueError('Exactly one captured SuperDelayFactor required')
    other = delivery.get('conditional_dbm', {}).get('importer_vf_settings', [])
    validate_settings_rows(list(other))
    conflicts = [row for row in other if ascii_equal(row['Parameter'], 'SuperDelayFactor')]
    if conflicts and conflicts != factors:
        raise ValueError('Captured Importer VFSettings factor declarations differ')
    if current and current != [factors[0]['Value']]:
        raise ValueError('Current DBM and captured Importer SuperDelayFactor differ')
    return factors[0]['Value']


def write_sources(run, output, *, opening=None, _sources=None, _bpr_history=None):
    if transaction.get_autocommit():
        raise ValueError('Daily sources require the calculation publication transaction')
    images = {}
    # Supplier inputs are captured before refresh. They are NOT the opening
    # BORWithOrderAllocation output, nor a replacement for that missing producer.
    prior = opening or {}
    if _bpr_history is not None and (_sources is None or 'production_report_policy' not in prior):
        raise ValueError('Completed BPR history requires scoped production sources')
    if _sources is not None and (('production_report_policy' in prior)
                                 != (_sources.production_reports is not None)):
        raise ValueError('Scoped production report source opt-in differs')
    for name in ('SOBData', 'MOQData'):
        rows = prior.get('supplier', {}).get(name)
        if rows is not None:
            path = 'opening/supplier/' + name
            if name == 'SOBData':
                from mta.presentation.daily_opening_sob import save
                images[path] = save(run, rows)
                continue
            images[path] = save_image(run, path, 'closing/supplier/' + name, rows)
            if load_image(run, images[path]) != storage(rows):
                raise ValueError('Supplier opening typed readback differs: ' + name)
    color = output.get('BPRFinal', [{}])[0].get('ColorSequence')
    if color is not None:
        if any(set(row) != {'Color', 'SequenceNo'} for row in color):
            raise ValueError('Daily ColorSequence field drift')
        DailyColorSequence.objects.bulk_create([DailyColorSequence(run=run, ordinal=i, **row)
                                                for i, row in enumerate(color)])
        rows = list(DailyColorSequence.objects.filter(run=run).order_by('ordinal').values('Color', 'SequenceNo'))
        if storage(rows) != storage(color):
            raise ValueError('Daily ColorSequence typed readback differs')
        images[COLOR_PATH] = dict(image=COLOR_PATH, table=DailyColorSequence._meta.db_table,
            count=len(rows), digest=digest(rows), fields=[['Color','Color','str'], ['SequenceNo','SequenceNo','int']])
    from mta.presentation import daily_requests
    from mta.runtime.models import DailyRequestCapture
    if DailyRequestCapture.objects.filter(run=run).exists():
        images[daily_requests.PATH] = daily_requests.metadata(run)
    from mta.presentation.ancillary_live import publication_metadata
    images.update(publication_metadata(run))
    from mta.presentation.terminal_scoped_remarks import publish as scoped_terminal_remarks
    images.update(scoped_terminal_remarks(run))
    if 'production_report_policy' in prior:
        from mta.presentation.production_reports import write as write_reports, _write_report_rows
        if _bpr_history is not None:
            from mta.runtime.bpr_history_completion import publish
            images.update(publish(run, _sources.production_reports, prior, _bpr_history))
        else:
            images.update(write_reports(run, output, prior) if _sources is None
                          else _write_report_rows(run,_sources.production_reports,prior))
    if prior.get('shipment_input') is not None:
        from mta.presentation.daily_transit import publish as publish_transit
        def current(path):
            return load_image(run, run.production_manifest['images'][path])
        settings_rows = current('closing/dbm/VFSettings')
        factor = _transit_factor(run, settings_rows)
        directory_source = prior.get('transporter_input')
        if directory_source is not None:
            from mta.application.production_source_inputs import validate, SCHEMA
            # The frozen-input validator retains its upstream list contract.
            # Adapt only these post-DBM owned rows; never copy the closing graph.
            from mta.row_sequences import RecordRows
            def source_rows(value):
                return dict(value, rows=list(value['rows'])) if isinstance(value['rows'], RecordRows) else value
            validate(dict(schema=prior.get('production_report_schema', SCHEMA), shipments=source_rows(prior['shipment_input']),
                          transporters=source_rows(directory_source), report_policy=prior['production_report_policy'],
                          report_opening=prior['production_report_opening']), run.business_date.isoformat())
            directory = directory_source['rows']
        else:
            directory = current('closing/consumer_context/GoodsInTransitTransporterMaster')
        images.update(publish_transit(run, prior['shipment_input'],
            standards=current('closing/dbm/SKULocStandardAttributes'),
            directory=directory,
            rationed_report=current('reports/bpr/vf_RationedReqReport'),
            super_delay_factor=factor,
            run_timestamp=datetime.combine(run.business_date, datetime.min.time())))
    if len(json.dumps(images)) > 65536:
        raise ValueError('Daily source metadata exceeds finite bound')
    return DailySourceReceipt.objects.create(run=run, input_digest=run.input_digest,
        recipe_digest=recipe_digest(), images=images, images_digest=digest(images))


@once_per_request
def receipt(run):
    value = DailySourceReceipt.objects.get(run=run)
    if (value.input_digest != run.input_digest or value.recipe_digest not in (
            recipe_digest(), RETAINED_V5_RECIPE, RETAINED_V6_RECIPE, RETAINED_ACTION_ADMISSION_RECIPE)
            or value.images_digest != digest(value.images)):
        raise ValueError('Daily source publication identity drift')
    if value.recipe_digest == RETAINED_V5_RECIPE and any(
            item.get('table', '').startswith('bpr_history/') for item in value.images.values()):
        raise ValueError('Historical source recipe cannot own late BPR history')
    return value


def image_metadata(run, path):
    from mta.presentation.context import PublicationUnavailable
    item = receipt(run).images.get(path)
    if item is None:
        raise PublicationUnavailable('daily_producer_not_published:' + path)
    return item


def image_rows(run, path):
    item = image_metadata(run, path)
    from mta.presentation import terminal_scoped_remarks
    if item.get('table')==terminal_scoped_remarks.TABLE:
        return terminal_scoped_remarks.read(run,item)
    if item.get('table', '').startswith('bpr_history/'):
        from mta.runtime.bpr_history_completion import read_published
        return read_published(run, path, item)
    from mta.presentation import daily_opening_sob
    if path == daily_opening_sob.PATH:
        return daily_opening_sob.read(run, item)
    from mta.presentation import daily_transit
    if path in daily_transit.MODELS:
        return daily_transit.read_rows(run, path, item)
    from mta.presentation import ancillary_live
    if path in ancillary_live.PATHS.values():
        if ancillary_live.image_metadata(run, path) != item:
            raise ValueError('Daily remark publication metadata drift')
        return ancillary_live.image_rows(run, path)
    from mta.presentation import daily_requests
    if path == daily_requests.PATH:
        if daily_requests.metadata(run) != item:
            raise ValueError('Daily request publication metadata drift')
        return daily_requests.rows(run)
    if path == COLOR_PATH:
        records = list(DailyColorSequence.objects.filter(run=run).order_by('ordinal').values('ordinal','Color','SequenceNo'))
        if [row.pop('ordinal') for row in records] != list(range(item['count'])) or digest(records) != item['digest']:
            raise ValueError('Daily ColorSequence population/value drift')
        return records
    return load_image(run, item)
