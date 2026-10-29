"""Internal reconstruction of input populations after their owning admission.

This is a decoder, not an admission or permissions boundary. Callers select and
authorize the owner before entering it. Existing diagnostic readers remain the
independent audit path. No graph or authority is retained between calls.
"""
from copy import deepcopy
from itertools import repeat
from typing import Callable

from django.db import connection

from mta.row_sequences import RecordRows
from mta.runtime.accepted_state_read import load_accepted_image
from mta.runtime.relational_state import quote, wire_value

V2 = 'fresh-daily-input-manifest-v2'
V3 = 'fresh-daily-input-manifest-v3'
CAPTURED = tuple('fresh-captured-input-reference-v' + str(version) for version in range(1, 7))


def _records(cursor):
    while rows := cursor.fetchmany(500):
        yield from rows


def _load_opening_image(owner, item):
    from mta.runtime.opening_storage import table_sql
    fields = item['fields']

    def records():
        with connection.chunked_cursor() as cursor:
            cursor.execute('SELECT vf_ordinal' +
                (' ,' + ','.join(quote(name) for _, name, _ in fields) if fields else '') +
                ' FROM ' + table_sql(item['table']) +
                ' WHERE vf_initialization_id=%s AND vf_image=%s ORDER BY vf_ordinal',
                [owner.pk, item['image']])
            for record in _records(cursor):
                yield {field: wire_value(value, kind)
                       for (field, _, kind), value in zip(fields, record[1:])}
    return RecordRows(item['count'], records) if item['count'] > 10000 else list(records())


def _iter_accepted_batch(attempt, entry):
    from mta.runtime.batch_storage import TABLES, TEMPORAL_KINDS, table_sql
    fields = entry['fields']
    kinds = dict(TABLES[entry['filename']]['columns'])
    temporal = [(field, native) for field, native, _ in fields if kinds[native] in TEMPORAL_KINDS]
    selected = [native for _, native, _ in fields] + ['vf_wire_' + native for _, native in temporal]
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT vf_ordinal' + (',' + ','.join(quote(name) for name in selected) if selected else '') +
            ' FROM ' + table_sql(entry['filename']) + ' WHERE vf_attempt_id=%s ORDER BY vf_ordinal',
            [str(attempt.attempt_id)])
        for record in _records(cursor):
            values = record[1:1 + len(fields)]
            wires = {field: wire for (field, _), wire in zip(temporal, record[1 + len(fields):])}
            yield {field: wires[field] if field in wires else wire_value(value, kind)
                   for (field, _, kind), value in zip(fields, values)}


def _raw_master(rows, snapshot, reference):
    """The existing raw NMS projection and frozen overlays, without admission.

    Streaming the NMS branch avoids ordinal lookups repeatedly reopening a lazy
    image. Description membership and overlay indexes are projection work.
    """
    from mta.application.persistent_master import NmsMasterRows
    from mta.mdm.daily_input import CompositionOverlayPlan, description_additions, nms_master_row
    additions = description_additions(snapshot['rows'], (nms_master_row(item) for item in rows))
    overlays = CompositionOverlayPlan(snapshot['rows'])

    def records():
        for item in rows:
            yield overlays.apply(nms_master_row(item))
        for item in additions:
            yield overlays.apply(deepcopy(item))

    view = RecordRows(len(rows) + len(additions), records)

    class RawPlan:
        def view(self, *, canonical=False):
            return view
    return NmsMasterRows(rows, canonical=False, reference=reference, plan=RawPlan())


def _node_at(manifest, path):
    node = manifest['tree']
    for key in path.split('/')[1:]:
        for name, child in node['object']:
            if name == key:
                node = child
                break
        else:
            raise KeyError(path)
    return node


def _at(value, path):
    for key in path.split('/')[1:]:
        value = value[key]
    return value


def read_accepted_input(owner, *, components=None, materialized_roots=(),
                        _image_reader: Callable | None = None,
                        _owner_resolver: Callable | None = None,
                        _batch_resolver: Callable | None = None,
                        _run_resolver: Callable | None = None):
    """Decode accepted V2/V3 and declared captured-origin manifests.

    Private callbacks provide cursor-free resolver fixtures; they are not trust
    switches. Production resolution uses the declared ORM owners and row keys.
    """
    def run_target(current, identifier):
        if _run_resolver is not None:
            return _run_resolver(current, identifier)
        from mta.runtime.models import CalculationRun
        return CalculationRun.objects.get(pk=identifier)

    def image(current, item):
        if _image_reader is not None:
            return _image_reader(current, item)
        if getattr(getattr(current, '_meta', None), 'model_name', None) == 'productioninitialization':
            return _load_opening_image(current, item)
        return load_accepted_image(current, item)

    def read(current, selected, roots):
        manifest = current.input_payload
        schema = manifest['schema']
        if schema in CAPTURED:
            identifier = (manifest['physical_origin_run_id'] if 'physical_origin_run_id' in manifest
                          else manifest['origin_run_id'])
            return read(run_target(current, identifier), selected, roots)
        if schema not in (V2, V3):
            raise ValueError('Accepted input decoder requires typed input')
        # Only collections needed by this reconstruction/one-hop aliases are
        # shared locally. Nothing survives a read or caches a returned graph.
        collections = {}

        def physical(path):
            return image(current, manifest['images'][path])

        def rebuild(template, row):
            if template[0] == 'dict':
                return {name: rebuild(child, row) for name, child in template[1]}
            if template[0] == 'list':
                return []
            return row['/'.join(template[1])]

        def unpack(node, path):
            if path in collections:
                return collections[path]
            if 'reference' in node:
                target = node['reference']
                return deepcopy(unpack(_node_at(manifest, target), target))
            if 'owner_reference' in node:
                reference = manifest['owner_references'][path]
                if _owner_resolver is not None:
                    target = _owner_resolver(current, reference)
                elif reference['kind'] == 'INITIALIZATION':
                    from mta.runtime.initialization_models import ProductionInitialization
                    target = ProductionInitialization.objects.get(pk=reference['owner_id'])
                elif reference['kind'] == 'RUN':
                    target = run_target(current, reference['owner_id'])
                else:
                    raise ValueError('Unsupported accepted input owner kind')
                component = reference['path'].removeprefix('input/')
                result = _at(read(target, (component,), ()), reference['path'])
            elif 'batch_reference' in node:
                reference = manifest['batch_references'][path]
                if _batch_resolver is not None:
                    attempt = _batch_resolver(current, reference['attempt_id'])
                else:
                    from mta.runtime.daily_feed_models import DailyFeedAttempt
                    attempt = DailyFeedAttempt.objects.get(attempt_id=reference['attempt_id'])
                entry = next(item for item in attempt.accepted_facts['feeds']
                             if item['filename'] == reference['filename'])
                factory = lambda: _iter_accepted_batch(attempt, entry)
                result = RecordRows(reference['count'], factory) if reference['count'] > 10000 else list(factory())
            elif 'derived_master' in node:
                reference = manifest['derived_references'][path]
                parent = run_target(current, reference['run_id'])
                rows = image(parent, parent.production_manifest['images']['closing/consumer_context/NMSAllItems'])
                snapshot = unpack(_node_at(manifest, 'input/mdm_input'), 'input/mdm_input')
                result = _raw_master(rows, snapshot, reference)
            elif 'scalar' in node:
                return node['scalar']
            elif 'empty' in node:
                return []
            elif 'object' in node:
                return {name: unpack(child, path + '/' + name) for name, child in node['object']}
            elif 'scalars' in node:
                return [row['value'] for row in physical(node['scalars'])]
            else:
                if 'shape' in node:
                    count = node['count']
                    scalars = physical(node['records']) if node['records'] else RecordRows(count, lambda: ({} for _ in range(count)))

                    def records():
                        for template, row in zip(repeat(node['shape'], count), scalars):
                            yield rebuild(template, row)
                else:
                    types = physical(node['shape_image'])
                    count = len(types)
                    scalars = physical(node['records']) if node['records'] else [{} for _ in types]

                    def records():
                        for item, row in zip(types, scalars):
                            yield rebuild(node['shapes'][item['shape_id']], row)
                materialized = any(path == root or path.startswith(root + '/') for root in roots)
                result = RecordRows(count, records) if not materialized and not node['children'] and count > 10000 else list(records())
                for field, child, link in node['children']:
                    values = unpack(child, path + '/children/' + '/'.join(field))
                    for item, value in zip(physical(link), values):
                        target = result[item['parent_ordinal']]
                        for key in field:
                            target = target[key]
                        target.append(value)
            collections[path] = result
            return result

        tree = manifest['tree']
        if selected is not None:
            if schema == V2:
                tree = {'object': [[name, node] for name, node in tree['object'] if name in selected]}
            else:
                requested = [name if name.startswith('input/') else 'input/' + name for name in selected]

                def prune(node, path):
                    if path in requested:
                        return node
                    children = [[name, chosen] for name, child in node.get('object', [])
                                if (chosen := prune(child, path + '/' + name)) is not None]
                    return {'object': children} if children else None
                tree = prune(tree, 'input') or {'object': []}
        return unpack(tree, 'input')
    return read(owner, components, materialized_roots)
