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


def recipe_digest():
    from mta.presentation.daily_transit import recipe_digest as transit_recipe
    from mta.presentation.daily_opening_sob import recipe_digest as sob_recipe
    from mta.presentation.production_reports import recipe_digest as report_recipe
    return digest(dict(version=4, writer=inspect.getsource(write_sources), sob=sob_recipe(),
                       transit=transit_recipe(), reports=report_recipe()))


def write_sources(run, output, *, opening=None):
    if transaction.get_autocommit():
        raise ValueError('Daily sources require the calculation publication transaction')
    images = {}
    # Supplier inputs are captured before refresh. They are NOT the opening
    # BORWithOrderAllocation output, nor a replacement for that missing producer.
    prior = opening or {}
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
    if 'production_report_policy' in prior:
        from mta.presentation.production_reports import write as write_reports
        images.update(write_reports(run, output, prior))
    if prior.get('shipment_input') is not None:
        from mta.presentation.daily_transit import publish as publish_transit
        def current(path):
            return load_image(run, run.production_manifest['images'][path])
        settings_rows = current('closing/dbm/VFSettings')
        factors = [row['Value'] for row in settings_rows if row['Parameter'] == 'SuperDelayFactor']
        if len(factors) != 1:
            raise ValueError('Exactly one current SuperDelayFactor required')
        directory_source = prior.get('transporter_input')
        if directory_source is not None:
            from mta.application.production_source_inputs import validate, SCHEMA
            validate(dict(schema=prior.get('production_report_schema', SCHEMA), shipments=prior['shipment_input'],
                          transporters=directory_source, report_policy=prior['production_report_policy'],
                          report_opening=prior['production_report_opening']), run.business_date.isoformat())
            directory = directory_source['rows']
        else:
            directory = current('closing/consumer_context/GoodsInTransitTransporterMaster')
        images.update(publish_transit(run, prior['shipment_input'],
            standards=current('closing/dbm/SKULocStandardAttributes'),
            directory=directory,
            rationed_report=current('reports/bpr/vf_RationedReqReport'),
            super_delay_factor=factors[0],
            run_timestamp=datetime.combine(run.business_date, datetime.min.time())))
    if len(json.dumps(images)) > 65536:
        raise ValueError('Daily source metadata exceeds finite bound')
    return DailySourceReceipt.objects.create(run=run, input_digest=run.input_digest,
        recipe_digest=recipe_digest(), images=images, images_digest=digest(images))


@once_per_request
def receipt(run):
    value = DailySourceReceipt.objects.get(run=run)
    if (value.input_digest != run.input_digest or value.recipe_digest != recipe_digest()
            or value.images_digest != digest(value.images)):
        raise ValueError('Daily source publication identity drift')
    return value


def image_metadata(run, path):
    from mta.presentation.context import PublicationUnavailable
    item = receipt(run).images.get(path)
    if item is None:
        raise PublicationUnavailable('daily_producer_not_published:' + path)
    return item


def image_rows(run, path):
    item = image_metadata(run, path)
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
