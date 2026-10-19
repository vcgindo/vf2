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
from mta.serialization import digest, canonical_parts
from mta.row_sequences import RecordRows, is_record_rows
from mta.application.streamed_input import StreamedInput

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


def create(value, destination, *, streamed=False):
    """Developer pack writer; all row populations are CSV, never output seeds."""
    checksum = hashlib.sha256()
    for part in canonical_parts(value, ensure_ascii=False):checksum.update(part)
    native_sha256 = checksum.hexdigest()
    raw = StreamedInput(value, native_sha256)
    configuration, recipe = digest(value['configuration']), digest(value['recipe'])
    decode(raw, native_sha256, expected_configuration=configuration,
           expected_recipe=recipe)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    populations = {}

    def pack(item, path='input'):
        if isinstance(item, dict):
            if '$csv' in item:
                raise ValueError('Reserved CSV reference key')
            return {key: pack(child, path + '/' + key) for key, child in item.items()}
        if not is_record_rows(item):
            return item
        native = _native_path(path)
        scalar = native in SCALARS
        rows = ([{'value': child} for child in item] if scalar else
            RecordRows(len(item), lambda: (_flatten(row) for row in item)))
        names = list(rows[0]) if rows else (['_empty'] if native in EMPTY_STRUCTURES
            else list(schema(native if scalar else native + '/values', [])[1]))
        types = {name:set() for name in names}
        for row in rows:
            if set(row) != set(names):raise ValueError('CSV population has inconsistent field rosters: ' + path)
            for name in names:
                if row[name] is not None:types[name].add(type(row[name]))
        columns = []
        for name in names:
            kinds = types[name]
            if kinds <= {str}:kind = 'text'
            elif kinds <= {int,float}:kind = 'number'
            elif kinds <= {int,bool}:kind = 'bit'
            else:raise ValueError('Mixed scalar representations in CSV column: '+path+'/'+name)
            columns.append(dict(name=name,kind=kind))
        filename = f'{len(populations)+1:03d}-' + path.removeprefix('input/').replace('/', '-') + '.csv'
        with (destination / filename).open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream, lineterminator='\r\n')
            writer.writerow(names)
            for row in rows:
                writer.writerow([_cell(row[name]) for name in names])
        checksum = hashlib.sha256()
        with (destination / filename).open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):checksum.update(block)
        populations[filename] = dict(path=path, scalar=scalar, columns=columns,
            rows=len(rows), sha256=checksum.hexdigest())
        return {'$csv': filename}

    template = pack(value)
    manifest = dict(schema=SCHEMA, template=template, populations=populations,
        native_input_sha256=native_sha256,
        configuration_digest=configuration, recipe_digest=recipe)
    (destination / MANIFEST).write_bytes(_canonical(manifest))
    (destination / 'READY').write_bytes(b'')
    # Reconstruct using the production reader, not only the writer's own values.
    assembled = read_streamed(destination, hashlib.sha256((destination / MANIFEST).read_bytes()).hexdigest(),
                     expected_configuration=configuration, expected_recipe=recipe)
    # read_streamed verifies the complete canonical identity before returning.
    if assembled.sha256 != native_sha256:raise ValueError('CSV native identity differs')
    return manifest, assembled if streamed else _canonical(value)


def read_streamed(directory, expected_manifest_sha256, *, expected_configuration, expected_recipe):
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
        source = regular(root / filename, root)
        identity = (source.stat().st_size, source.stat().st_mtime_ns)
        checksum = hashlib.sha256()
        with source.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):checksum.update(block)
        if checksum.hexdigest() != spec['sha256']:
            raise ValueError('Opening CSV checksum differs: ' + filename)
        def records():
            regular(source, root)
            if (source.stat().st_size, source.stat().st_mtime_ns) != identity:
                raise ValueError('Opening CSV changed: ' + filename)
            try:
                with source.open('r', encoding='utf-8-sig', newline='') as stream:
                    reader = csv.reader(stream, strict=True)
                    if next(reader, None) != names:
                        raise ValueError('Opening CSV headers/order differ: ' + filename)
                    for ordinal, cells in enumerate(reader, 1):
                        if len(cells) != len(names):
                            raise ValueError(f'{filename}:record{ordinal}: CSV row width differs')
                        row = {}
                        for cell, column in zip(cells, spec['columns']):
                            try:value = _value(cell, column['kind'])
                            except ValueError as error:
                                raise ValueError(f'{filename}:record{ordinal}:{column["name"]}: {error}') from error
                            name = column['name']
                            if name.startswith('policy/'):
                                row.setdefault('policy', {})[name.removeprefix('policy/')] = value
                            else:row[name] = value
                        yield row
            except (UnicodeError, csv.Error) as error:
                raise ValueError('Malformed opening CSV: ' + filename) from error
            if (source.stat().st_size, source.stat().st_mtime_ns) != identity:
                raise ValueError('Opening CSV changed: ' + filename)
        if spec['scalar']:
            rows = [row['value'] for row in records()]
        elif path.startswith('input/opening/state/') and spec['rows'] > 10000:
            rows = RecordRows.from_rows(records())
        else:rows = list(records())
        # Validate every cell and population now, even for lazy histories.
        if sum(1 for _ in rows) != spec['rows']:
            raise ValueError('Opening CSV row count differs: ' + filename)
        return rows

    value = unpack(manifest['template'])
    if used != set(manifest['populations']):
        raise ValueError('Unreferenced opening CSV population')
    native = StreamedInput(value, manifest['native_input_sha256'])
    decode(native, manifest['native_input_sha256'], expected_configuration=expected_configuration,
           expected_recipe=expected_recipe)
    return native


def read(directory, expected_manifest_sha256, *, expected_configuration, expected_recipe):
    """Compatibility API for bounded callers needing canonical bytes."""
    value = read_streamed(directory, expected_manifest_sha256,
        expected_configuration=expected_configuration, expected_recipe=expected_recipe)
    return b''.join(canonical_parts(value.snapshot(value.sha256), ensure_ascii=False))
