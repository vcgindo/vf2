"""CSV format adapter for the existing atomic master/opening initializer.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import csv
import hashlib
import io
import json
from pathlib import Path
import re

from mta.application.production_csv_files import decode_json, regular
from mta.mdm.initialization_contract import decode
from mta.mdm.initialization_rows import SCALARS, EMPTY_STRUCTURES, schema
from mta.serialization import digest

SCHEMA = 'vectorflow-initialization-csv-v1'
MANIFEST = 'opening-manifest.json'


def _native_path(path):
    if path.startswith('input/masters/'):
        return path.replace('input/masters/', 'input/opening/state/', 1)
    return path.replace('input/configuration/', 'input/profile/', 1)


def _flatten(row):
    result = {}
    for key, value in row.items():
        if key == 'policy' and isinstance(value, dict):
            result.update({'policy/' + name: item for name, item in value.items()})
        elif isinstance(value, (dict, list)):
            raise ValueError('Unsupported nested CSV record field: ' + key)
        else:
            result[key] = value
    return result


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _cell(value):
    if value is None:
        return '\\N'
    if type(value) is str:
        if value == '\\N':
            raise ValueError('Literal reserved CSV NULL token is not supported')
        return value
    return json.dumps(value, allow_nan=False)


def _value(cell, kind):
    if cell == '\\N':
        return None
    if kind == 'text':
        return cell
    if kind not in ('number', 'bit'):
        raise ValueError('Unknown CSV scalar type')
    if not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|true|false', cell):
        raise ValueError('Invalid CSV ' + kind + ': ' + cell[:100])
    result = json.loads(cell)
    if kind == 'number' and type(result) not in (int, float):
        raise ValueError('A numeric CSV value is required')
    if kind == 'bit' and (type(result) not in (bool, int) or result not in (0, 1)):
        raise ValueError('A boolean or0/1 CSV value is required')
    return result


def create(value, destination):
    """Developer pack writer; all row populations are CSV, never output seeds."""
    raw = _canonical(value)
    configuration, recipe = digest(value['configuration']), digest(value['recipe'])
    decode(raw, hashlib.sha256(raw).hexdigest(), expected_configuration=configuration,
           expected_recipe=recipe)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    populations = {}

    def pack(item, path='input'):
        if isinstance(item, dict):
            if '$csv' in item:
                raise ValueError('Reserved CSV reference key')
            return {key: pack(child, path + '/' + key) for key, child in item.items()}
        if not isinstance(item, list):
            return item
        native = _native_path(path)
        scalar = native in SCALARS
        rows = [{'value': child} for child in item] if scalar else [_flatten(row) for row in item]
        if rows:
            names = list(rows[0])
            if any(set(row) != set(names) for row in rows):
                raise ValueError('CSV population has inconsistent field rosters: ' + path)
        elif native in EMPTY_STRUCTURES:
            names = ['_empty']
        else:
            _, fields = schema(native if scalar else native + '/values', [])
            names = list(fields)
        columns = []
        for name in names:
            types = {type(row[name]) for row in rows if row[name] is not None}
            if types <= {str}:
                kind = 'text'
            elif types <= {int, float}:
                kind = 'number'
            elif types <= {int, bool}:
                kind = 'bit'
            else:
                raise ValueError('Mixed scalar representations in CSV column: ' + path + '/' + name)
            columns.append(dict(name=name, kind=kind))
        filename = f'{len(populations)+1:03d}-' + path.removeprefix('input/').replace('/', '-') + '.csv'
        stream = io.StringIO(newline='')
        writer = csv.writer(stream, lineterminator='\r\n')
        writer.writerow(names)
        for row in rows:
            writer.writerow([_cell(row[name]) for name in names])
        payload = stream.getvalue().encode('utf-8')
        (destination / filename).write_bytes(payload)
        populations[filename] = dict(path=path, scalar=scalar, columns=columns,
            rows=len(rows), sha256=hashlib.sha256(payload).hexdigest())
        return {'$csv': filename}

    template = pack(value)
    manifest = dict(schema=SCHEMA, template=template, populations=populations,
        native_input_sha256=hashlib.sha256(raw).hexdigest(),
        configuration_digest=configuration, recipe_digest=recipe)
    (destination / MANIFEST).write_bytes(_canonical(manifest))
    (destination / 'READY').write_bytes(b'')
    # Reconstruct using the production reader, not only the writer's own values.
    assembled = read(destination, hashlib.sha256((destination / MANIFEST).read_bytes()).hexdigest(),
                     expected_configuration=configuration, expected_recipe=recipe)
    if assembled != raw:
        raise ValueError('CSV pack does not reconstruct the exact native input')
    return manifest, assembled


def read(directory, expected_manifest_sha256, *, expected_configuration, expected_recipe):
    """Read and fully validate every byte BEFORE entering the native initializer."""
    root = Path(directory).absolute()
    regular(root / 'READY', root)
    raw = regular(root / MANIFEST, root).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
        raise ValueError('Opening CSV manifest checksum differs')
    manifest = decode_json(raw)
    if (not isinstance(manifest, dict) or set(manifest) != {'schema', 'template', 'populations',
            'native_input_sha256', 'configuration_digest', 'recipe_digest'} or manifest['schema'] != SCHEMA
            or manifest['configuration_digest'] != expected_configuration
            or manifest['recipe_digest'] != expected_recipe or not isinstance(manifest['populations'], dict)):
        raise ValueError('Complete matching opening CSV manifest required')
    if set(p.name for p in root.iterdir()) != {MANIFEST, 'READY', *manifest['populations']}:
        raise ValueError('Opening CSV file roster differs')
    used = set()

    def unpack(item, path='input'):
        if isinstance(item, list):
            raise ValueError('Business row lists must be CSV references')
        if not isinstance(item, dict):
            return item
        if '$csv' not in item:
            return {key: unpack(child, path + '/' + key) for key, child in item.items()}
        filename = item['$csv']
        if (set(item) != {'$csv'} or not isinstance(filename, str)
                or not re.fullmatch(r'[a-zA-Z0-9_-]+\.csv', filename)
                or filename in used or filename not in manifest['populations']):
            raise ValueError('Invalid/duplicate opening CSV reference')
        used.add(filename)
        spec = manifest['populations'][filename]
        if (set(spec) != {'path', 'scalar', 'columns', 'rows', 'sha256'} or spec['path'] != path
                or type(spec['scalar']) is not bool or type(spec['rows']) is not int or spec['rows'] < 0
                or not isinstance(spec['columns'], list) or not spec['columns']):
            raise ValueError('Invalid opening CSV population declaration')
        names = [c['name'] for c in spec['columns']]
        if (len(set(names)) != len(names) or any(set(c) != {'name', 'kind'}
                or not isinstance(c['name'], str) or c['kind'] not in ('text', 'number', 'bit')
                for c in spec['columns'])):
            raise ValueError('Invalid opening CSV columns')
        payload = regular(root / filename, root).read_bytes()
        if hashlib.sha256(payload).hexdigest() != spec['sha256']:
            raise ValueError('Opening CSV checksum differs: ' + filename)
        try:
            reader = csv.reader(io.StringIO(payload.decode('utf-8-sig'), newline=''), strict=True)
            if next(reader, None) != names:
                raise ValueError('Opening CSV headers/order differ: ' + filename)
            rows = []
            for ordinal, cells in enumerate(reader, 1):
                if len(cells) != len(names):
                    raise ValueError(f'{filename}:record{ordinal}: CSV row width differs')
                row = {}
                for cell, column in zip(cells, spec['columns']):
                    try:
                        value = _value(cell, column['kind'])
                    except ValueError as error:
                        raise ValueError(f'{filename}:record{ordinal}:{column["name"]}: {error}') from error
                    name = column['name']
                    if name.startswith('policy/'):
                        row.setdefault('policy', {})[name.removeprefix('policy/')] = value
                    else:
                        row[name] = value
                rows.append(row['value'] if spec['scalar'] else row)
        except (UnicodeError, csv.Error) as error:
            raise ValueError('Malformed opening CSV: ' + filename) from error
        if len(rows) != spec['rows']:
            raise ValueError('Opening CSV row count differs: ' + filename)
        return rows

    value = unpack(manifest['template'])
    if used != set(manifest['populations']):
        raise ValueError('Unreferenced opening CSV population')
    native = _canonical(value)
    decode(native, manifest['native_input_sha256'], expected_configuration=expected_configuration,
           expected_recipe=expected_recipe)
    return native
