"""Version-three typed input manifests with same-owner logical aliases.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

This module is deliberately restricted to input storage.  It does not change
calculation, SQL selection, action policy, frontend, MTO, authentication, or
daily ownership.  References are explicit one-hop aliases between exactly
equal collections owned by the same immutable initialization or successful
run; cross-owner daily staging belongs to M3 and is rejected here.
"""
from collections.abc import Sequence
from copy import deepcopy
from uuid import UUID

from django.db import connection

from mta.row_sequences import RecordRows
from mta.serialization import canonical_parts, digest, storage


V3 = 'fresh-daily-input-manifest-v3'
IDENTITY_FIELDS = frozenset(('database_name', 'database_oid', 'source_digest',
                             'owner_kind', 'owner_id'))


def _database_identity():
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(),oid::bigint FROM pg_database '
                       'WHERE datname=current_database()')
        row = cursor.fetchone()
    if not row:
        raise ValueError('Typed input database identity unavailable')
    return row


def _live_identity(owner, *, reading):
    """Resolve production identity from the database, never caller metadata."""
    meta = getattr(owner, '_meta', None)
    model_name = getattr(meta, 'model_name', None)
    if model_name == 'productioninitialization':
        current = type(owner).objects.select_related('source').only('id','source__digest','input_manifest_digest').get(pk=owner.pk)
        if reading and not current.input_manifest_digest:
            raise ValueError('Typed input initialization owner is mutable')
        owner_kind = 'initialization'
        source_digest = current.source.digest
    elif model_name == 'calculationrun':
        current = type(owner).objects.get(pk=owner.pk)
        if current.status != 'SUCCEEDED':
            raise ValueError('Typed input run owner is mutable')
        owner_kind = 'run'
        try:
            source_digest = current.mdm_input_capture.source.digest
        except (AttributeError, ObjectDoesNotExist):
            try:
                source_digest = current.csv_attempt.initialization.source.digest
            except (AttributeError, ObjectDoesNotExist) as error:
                raise ValueError('Typed input run source identity unavailable') from error
    else:
        raise ValueError('Typed input owner kind is unsupported')
    database_name, database_oid = _database_identity()
    return dict(database_name=database_name, database_oid=database_oid,
                source_digest=source_digest, owner_kind=owner_kind,
                owner_id=str(current.pk))


# Importing ObjectDoesNotExist after the function keeps the storage-only module
# cheap for pure tests while retaining a precise related-owner failure boundary.
from django.core.exceptions import ObjectDoesNotExist


def _identity(owner, resolver, *, reading):
    value = resolver(owner) if resolver is not None else _live_identity(owner, reading=reading)
    if not isinstance(value, dict) or set(value) != IDENTITY_FIELDS:
        raise ValueError('Typed input owner identity fields differ')
    if (not isinstance(value['database_name'], str) or not value['database_name']
            or type(value['database_oid']) is not int or value['database_oid'] <= 0
            or value['owner_kind'] not in ('initialization', 'run')
            or not isinstance(value['source_digest'], str)
            or len(value['source_digest']) != 64
            or any(c not in '0123456789abcdef' for c in value['source_digest'])):
        raise ValueError('Typed input owner identity value differs')
    try:
        owner_id = str(UUID(str(value['owner_id'])))
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError('Typed input owner UUID differs') from error
    if owner_id != str(value['owner_id']).lower() or owner_id != str(owner.pk).lower():
        raise ValueError('Typed input owner UUID differs')
    return {**value, 'owner_id': owner_id}


def _normal_path(value):
    if (not isinstance(value, str) or not value.startswith('input/')
            or value.endswith('/') or '//' in value or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Typed input alias path differs')
    return value


def _at(raw, path):
    value = raw
    for key in path.split('/')[1:]:
        if not isinstance(value, dict) or key not in value:
            raise ValueError('Typed input alias target is dangling: '+path)
        value = value[key]
    return value


def _collection(value):
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray, dict))


def _typed_equal(left, right):
    if _collection(left) or _collection(right):
        if not _collection(left) or not _collection(right) or len(left) != len(right):
            return False
        return all(_typed_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) or isinstance(right, dict):
        if not isinstance(left, dict) or not isinstance(right, dict) or list(left) != list(right):
            return False
        return all(_typed_equal(left[key], right[key]) for key in left)
    return type(left) is type(right) and left == right


def _aliases(raw, aliases):
    if aliases is None:
        return {}
    if not isinstance(aliases, dict):
        raise ValueError('Typed input aliases require an explicit mapping')
    result = {}
    for source, target in aliases.items():
        source, target = _normal_path(source), _normal_path(target)
        if source == target or source in result:
            raise ValueError('Typed input alias identity differs')
        result[source] = target
    if any(target in result for target in result.values()):
        raise ValueError('Typed input aliases must be one-hop')
    for source, target in result.items():
        source_value, target_value = _at(raw, source), _at(raw, target)
        if not _collection(source_value) or not _collection(target_value):
            raise ValueError('Typed input alias requires collection targets')
        if not _typed_equal(source_value, target_value):
            raise ValueError('Typed input alias population differs: '+source)
    return result


def save_input(owner, raw, *, image_writer, table_selector, aliases=None,
               identity_resolver=None, explicit_table_selector=False):
    """Write an opt-in v3 manifest; callers must persist its digest separately."""
    from mta.runtime import input_storage as common
    identity = _identity(owner, identity_resolver, reading=False)
    aliases = _aliases(raw, aliases)
    images = {}

    def image(path, rows, table=None):
        table = table or table_selector(rows[0] if rows else (), path, rows)
        images[path] = image_writer(owner, path, None, rows, table=table)
        return path

    def pack(value, path):
        if path in aliases:
            return {'reference': aliases[path]}
        if isinstance(value, dict):
            return {'object': [[key, pack(item, path+'/'+key)]
                               for key, item in value.items()]}
        if not _collection(value):
            return {'scalar': storage(value)}
        if not value:
            if explicit_table_selector:
                table = table_selector((), path+'/values', [])
            else:
                from mta.runtime.complete_daily_state import input_table
                table = input_table(path+'/values')
            if table is None:
                return {'empty': True}
            return {'records': image(path+'/values', [], table), 'shape': None,
                    'count': 0, 'children': []}
        if all(not isinstance(item, dict) and not _collection(item) for item in value):
            rows = common.Rows(len(value), lambda: ({'value': item} for item in value))
            kinds = {type(item) for item in value if item is not None}
            if kinds <= {int}:
                table = 'input/integer_values'
            elif kinds <= {str}:
                table = 'input/string_values'
            else:
                raise ValueError('Unsupported scalar input collection: '+path)
            return {'scalars': image(path, rows, table)}
        if not all(isinstance(row, dict) for row in value):
            raise ValueError('Input collection requires one declared record family: '+path)
        shapes, fields, children = [], [], []
        for row in value:
            item = common.shape(row)
            if item not in shapes:
                shapes.append(item)
                if len(shapes) > 128:
                    raise ValueError('Input record schema exceeds bounded shape contract')
                for leaf in common.leaves(item, 'value'):
                    if leaf not in fields:
                        fields.append(leaf)
                for child in common.leaves(item, 'list'):
                    if child not in children:
                        children.append(child)
        projected = common.Rows(len(value), lambda: ({'/'.join(field): common.get(row, field)
            for field in fields} for row in value))
        scalar_image = image(path+'/values', projected) if fields else None
        if len(shapes) == 1:
            result = {'records': scalar_image, 'shape': shapes[0],
                      'count': len(value), 'children': []}
        else:
            variants = common.Rows(len(value), lambda: ({'shape_id': shapes.index(common.shape(row))}
                                                         for row in value))
            result = {'records': scalar_image,
                      'shape_image': image(path+'/shape', variants, 'input/row_shape'),
                      'shapes': shapes, 'children': []}
        for field in children:
            length = sum(len(common.get(row, field, [])) for row in value)
            childrows = common.Rows(length, lambda field=field:
                (child for row in value for child in common.get(row, field, [])))
            links = common.Rows(length, lambda field=field:
                ({'parent_ordinal': index, 'child_ordinal': ordinal}
                 for index, row in enumerate(value)
                 for ordinal, _ in enumerate(common.get(row, field, []))))
            childpath = path+'/children/'+'/'.join(field)
            result['children'].append([list(field), pack(childrows, childpath),
                                       image(childpath+'/links', links, 'input/child_link')])
        return result

    tree = pack(raw, 'input')
    manifest = dict(schema=V3, tree=tree, images=images,
                    content_digest=owner.input_digest, identity=identity,
                    aliases=aliases,
                    profile={'delivery': {'site_code': raw['profile']['delivery']['site_code']}})
    if sum(len(part) for part in canonical_parts(manifest)) > 1024*1024:
        raise ValueError('Typed input metadata exceeds bounded manifest size')
    return manifest


def read_input(owner, *, components=None, image_reader, materialized_roots=(),
               identity_resolver=None):
    value = owner.input_payload
    if (value.get('schema') != V3 or value.get('content_digest') != owner.input_digest
            or digest(value) != owner.input_manifest_digest):
        raise ValueError('Typed daily input manifest identity drift')
    if value.get('identity') != _identity(owner, identity_resolver, reading=True):
        raise ValueError('Typed input live owner identity drift')
    aliases = value.get('aliases')
    if not isinstance(aliases, dict):
        raise ValueError('Typed input alias manifest differs')

    def node_at(path):
        node = value['tree']
        for key in _normal_path(path).split('/')[1:]:
            if 'object' not in node:
                raise ValueError('Typed input alias target is dangling: '+path)
            matches = [child for name, child in node['object'] if name == key]
            if len(matches) != 1:
                raise ValueError('Typed input alias target is dangling: '+path)
            node = matches[0]
        return node

    references = {}
    def inspect(node, path):
        if 'reference' in node:
            if set(node) != {'reference'} or aliases.get(path) != node['reference']:
                raise ValueError('Typed input alias reference differs')
            references[path] = node['reference']
            return
        if 'object' in node:
            for key, child in node['object']:
                inspect(child, path+'/'+key)
        for field, child, _ in node.get('children', []):
            inspect(child, path+'/children/'+'/'.join(field))
    inspect(value['tree'], 'input')
    if references != aliases or any(target in aliases for target in aliases.values()):
        raise ValueError('Typed input aliases must be explicit one-hop references')
    for source, target in aliases.items():
        _normal_path(source); _normal_path(target)
        target_node = node_at(target)
        if 'reference' in target_node or not any(key in target_node for key in
                ('empty', 'scalars', 'records', 'shape_image')):
            raise ValueError('Typed input alias target differs')

    def read(path):
        return image_reader(owner, value['images'][path])

    cache = {}
    resolving = set()
    def unpack(node, path):
        if path in cache:
            return cache[path]
        if 'reference' in node:
            target = node['reference']
            if target in resolving:
                raise ValueError('Typed input alias cycle')
            if target not in cache:
                resolving.add(target)
                cache[target] = unpack(node_at(target), target)
                resolving.remove(target)
            return deepcopy(cache[target])
        if 'scalar' in node:
            return node['scalar']
        if 'empty' in node:
            return []
        if 'object' in node:
            return {key: unpack(child, path+'/'+key) for key, child in node['object']}
        if 'scalars' in node:
            return [row['value'] for row in read(node['scalars'])]
        if 'shape' in node:
            count = node.get('count')
            if type(count) is not int or count < 0 or (node['shape'] is None) != (count == 0):
                raise ValueError('Typed input uniform shape identity drift')
            from itertools import repeat
            templates = None
            scalars = read(node['records']) if node['records'] else RecordRows(count, lambda: ({} for _ in range(count)))
        else:
            types = read(node['shape_image'])
            templates = []
            for item in types:
                shape_id = item['shape_id']
                if type(shape_id) is not int or not 0 <= shape_id < len(node['shapes']):
                    raise ValueError('Typed input shape identity drift')
                templates.append(node['shapes'][shape_id])
            scalars = read(node['records']) if node['records'] else [{} for _ in types]
        count = count if 'shape' in node else len(templates)
        if count != len(scalars):
            raise ValueError('Typed input shape population drift')

        def rebuild(template, row):
            if template[0] == 'dict':
                return {key: rebuild(child, row) for key, child in template[1]}
            if template[0] == 'list':
                return []
            return row['/'.join(template[1])]
        def records():
            for template, row in zip(repeat(node['shape'], count) if templates is None else templates, scalars):
                yield rebuild(template, row)
        materialized = any(path == root or path.startswith(root+'/')
                           for root in materialized_roots)
        rows = (RecordRows(count, records)
                if not materialized and not node['children'] and count > 10000
                else list(records()))
        for field, child, link in node['children']:
            child_path = path+'/children/'+'/'.join(field)
            values, links = unpack(child, child_path), read(link)
            if len(values) != len(links):
                raise ValueError('Typed input child population drift')
            for item, childvalue in zip(links, values):
                if (type(item.get('parent_ordinal')) is not int
                        or type(item.get('child_ordinal')) is not int
                        or not 0 <= item['parent_ordinal'] < len(rows)):
                    raise ValueError('Typed input child ownership/order drift')
                target = common_get(rows[item['parent_ordinal']], field)
                if not isinstance(target, list) or len(target) != item['child_ordinal']:
                    raise ValueError('Typed input child ownership/order drift')
                target.append(childvalue)
        cache[path] = rows
        return rows

    from mta.runtime.input_storage import get as common_get
    tree = value['tree']
    if components is not None:
        tree = {'object': [[key, child] for key, child in tree['object'] if key in components]}
    return unpack(tree, 'input')


# Finite lossless same-opening aliases. Distinct producer populations remain
# separate whenever any typed value, key order, duplicate or ordinal differs.
OPENING_ALIASES = {
    'input/opening/state/controls/importer_settings': 'input/opening/state/importer_settings',
    'input/opening/state/btr/SKUDescriptionTbl': 'input/opening/state/importer/SKUDescriptionTbl',
    'input/opening/state/dbm/SKUDescriptionTbl': 'input/opening/state/importer/SKUDescriptionTbl',
    'input/opening/state/btr/SiteDescriptionTbl': 'input/opening/state/importer/SiteDescriptionTbl',
    'input/opening/state/dbm/SiteDescriptionTbl': 'input/opening/state/importer/SiteDescriptionTbl',
}


def opening_aliases(frame):
    aliases = {}
    for source, target in OPENING_ALIASES.items():
        try:
            left, right = _at(frame, source), _at(frame, target)
        except ValueError:
            continue
        if _collection(left) and _collection(right) and _typed_equal(left, right):
            aliases[source] = target
    return aliases
