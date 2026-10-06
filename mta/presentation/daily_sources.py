"""Publish missing narrow sources while their owning daily outputs are available.

Existing closing/history images remain in the original production manifest. This
receipt adds source-stage metadata without changing the F2 output reconstruction.
No receipt is synthesized for absent logistics, remarks or BOR producers.
"""
import inspect
import json
from django.db import transaction
from mta.runtime.models import DailySourceReceipt, DailyColorSequence
from mta.runtime.relational_state import save_image, load_image
from mta.serialization import digest, storage

COLOR_PATH = 'metadata/bpr/ColorSequence'


def recipe_digest():
    return digest(dict(version=1, writer=inspect.getsource(write_sources)))


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
    if len(json.dumps(images)) > 65536:
        raise ValueError('Daily source metadata exceeds finite bound')
    return DailySourceReceipt.objects.create(run=run, input_digest=run.input_digest,
        recipe_digest=recipe_digest(), images=images, images_digest=digest(images))


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
    if path == COLOR_PATH:
        records = list(DailyColorSequence.objects.filter(run=run).order_by('ordinal').values('ordinal','Color','SequenceNo'))
        if [row.pop('ordinal') for row in records] != list(range(item['count'])) or digest(records) != item['digest']:
            raise ValueError('Daily ColorSequence population/value drift')
        return records
    return load_image(run, item)
