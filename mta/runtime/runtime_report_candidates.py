"""Private, immutable placement candidates; never database readiness.

The publication owner authenticates configuration/sources and supplies an owned
root. It must recheck its worker and generation before registering the result.
This component handles ordered projection/file effects and complete readback.
Old accepted directories are never edited: cleanup is an ordered catalogue
change for the registering owner, while overwritten bytes remain in old custody.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import stat
from uuid import UUID

from mta.application import operational_io as files
from mta.application import runtime_report_files as runtime_files
from mta.application import runtime_report_encoding as encoding
from mta.application.runtime_report_configuration import configuration, definition_digest, plan
from mta.application.runtime_report_projection import describe, project
from mta.serialization import digest

SCHEMA = 'fresh-runtime-report-candidate-v1'
LIMIT = 1024 * 1024
MANIFEST = 'candidate.json'


def _directory(root, identity):
    if type(identity) is not str or str(UUID(identity)) != identity:
        raise ValueError('Canonical runtime report candidate UUID required')
    return files.owned_path(root, identity)


def _sync(path):
    if os.name == 'posix':
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try: os.fsync(descriptor)
        finally: os.close(descriptor)


def _file(root, relative):
    path = files.owned_path(root, relative)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ValueError('Candidate file must be regular and have one link')
    value = files.inspect_file(root, relative)
    value['members'] = files.zip_members(root, relative) if relative.lower().endswith('.zip') else []
    after = path.stat()
    if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            or after.st_nlink != 1):
        raise ValueError('Candidate file changed during verification')
    return value


def _removals(layout):
    values = [layout['previous_csv'], layout['csv']]
    if layout['compression']:
        values += [layout['previous_output'], layout['output']]
    if layout['delete_old']:
        values.append(layout['previous_download'])
    values.append(layout['download'])
    return list(dict.fromkeys(values))


def _fold(reports, previous=None, *, candidate_id):
    result = deepcopy(previous or {})
    for report in reports:
        for path in report['remove']:
            result.pop(path, None)
        for value in report['write']:
            result[value['relative_path']] = dict(candidate_id=candidate_id, file=deepcopy(value))
    return result


def _roster(directory):
    result = set()
    for folder, directories, names in os.walk(directory, followlinks=False):
        for name in directories:
            if Path(folder, name).is_symlink():
                raise ValueError('Candidate directory links are forbidden')
        for name in names:
            relative = Path(folder, name).relative_to(directory).as_posix()
            files.owned_path(directory, relative)
            result.add(relative)
    return result


def materialize(*, root, candidate_id, report_configuration, placement, variables,
                last_generated, inputs, archive_writer=None):
    """Create one exclusive candidate from authenticated caller-supplied bags.

    inputs maps each selected Id to sources/provenance from its qualified source
    adapter. This API intentionally does not confer authority on those inputs.
    Registration must bind the captured configuration, source and recipe again.
    """
    checked = configuration(report_configuration)
    if (type(last_generated) is not list or any(type(row) is not dict
            or set(row) != {'Id', 'LastGeneratedFileName'} or type(row['Id']) is not int
            for row in last_generated)):
        raise ValueError('Explicit generated filename state required')
    names = {row['Id']: row['LastGeneratedFileName'] for row in last_generated}
    if (len(names) != len(last_generated)
            or set(names) != {row['Id'] for row in checked['RuntimeReports']}):
        raise ValueError('Generated filename state roster differs')
    effective = deepcopy(checked)
    for row in effective['RuntimeReports']:
        row['LastGeneratedFileName'] = names[row['Id']]
    # Filename state evolves separately from the immutable captured definition.
    stages = [stage for stage in plan(effective, 'Full') if stage['placement'] == placement]
    if len(stages) != 1 or stages[0]['DownloadableUIReportSettings']:
        raise ValueError('Explicit RuntimeReports-only placement candidate required')
    definitions = stages[0]['RuntimeReports']
    if type(inputs) is not dict or set(inputs) != {row['Id'] for row in definitions}:
        raise ValueError('Exact placement report input roster required')
    layouts, aliases = {}, {}
    for row in definitions:
        item = inputs[row['Id']]
        if (type(item) is not dict or set(item) != {'sources', 'provenance'}
                or type(item['provenance']) is not dict
                or item['provenance'].get('query_sha256') != describe(row)['query_sha256']):
            raise ValueError('Explicit query-bound report source provenance required')
        layout = runtime_files.layout(row, variables)
        encoding.chunks(row, ())  # Validate the format before creating files.
        if layout['compression'] and not callable(archive_writer):
            raise ValueError('Qualified archive writer required')
        layouts[row['Id']] = layout
        for path in (*_removals(layout), layout['output']):
            # Windows's differently spelled path aliases are not silently
            # treated as independent Linux files. Exact same-path overwrites
            # remain supported in the canonical report Id order.
            folded = path.lower()
            if folded in aliases and aliases[folded] != path:
                raise ValueError('Runtime report path-case alias requires qualification')
            aliases[folded] = path
    directory = _directory(root, candidate_id)
    directory.mkdir(mode=0o700)  # Exclusive, including abandoned failed attempts.
    _sync(directory.parent)
    reports = []
    for row in definitions:
        item, layout = inputs[row['Id']], layouts[row['Id']]
        result = project(row, item['sources'])
        receipt = runtime_files.publish(root=directory, definition=row, variables=variables,
            report_chunks=encoding.chunks(row, result['rows']), archive_writer=archive_writer)
        surviving = [_file(directory, receipt[name]['relative_path']) for name in ('output', 'download')]
        reports.append(dict(report_id=row['Id'], definition_digest=digest({
                key:value for key,value in row.items() if key != 'LastGeneratedFileName'}),
            source=deepcopy(item['provenance']), last_generated_file_name=receipt['last_generated_file_name'],
            remove=_removals(layout), write=surviving))
        names[row['Id']] = receipt['last_generated_file_name']
    visible = _fold(reports, candidate_id=candidate_id)
    manifest = dict(schema=SCHEMA, candidate_id=candidate_id, placement=placement,
        configuration_digest=digest(checked), definition_digest=definition_digest(checked),
        variables_digest=digest(variables), reports=reports,
        last_generated_before=deepcopy(last_generated),
        last_generated_after=[dict(Id=row['Id'], LastGeneratedFileName=names[row['Id']]) for row in last_generated],
        files={path: entry['file'] for path, entry in sorted(visible.items())})
    manifest['digest'] = digest(manifest)
    payload = (json.dumps(manifest, sort_keys=True, ensure_ascii=True, allow_nan=False)+'\n').encode()
    if len(payload) > LIMIT:
        raise ValueError('Runtime candidate metadata exceeds bound')
    # Recheck the final surviving roster after later reports have performed
    # their canonical deletions/overwrites; removed source CSVs are not files.
    if _roster(directory) != set(manifest['files']):
        raise ValueError('Candidate surviving file roster differs')
    for path, value in manifest['files'].items():
        if _file(directory, path) != value:
            raise ValueError('Candidate surviving file bytes differ')
    files.write_file(directory, MANIFEST, payload)
    for folder, _directories, _names in os.walk(directory, topdown=False):
        _sync(folder)
    return verify(root=root, candidate_id=candidate_id, expected_digest=manifest['digest'])


def verify(*, root, candidate_id, expected_digest):
    """Verify a completed private candidate, without replay or registration."""
    from mta.application.runtime_report_configuration import _pairs, _nonfinite
    directory = _directory(root, candidate_id)
    if files.owned_path(directory, MANIFEST).stat().st_size > LIMIT:
        raise ValueError('Runtime candidate metadata exceeds bound')
    _file(directory, MANIFEST)
    with files.owned_path(directory, MANIFEST).open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Runtime candidate metadata exceeds bound')
    value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite)
    if (type(value) is not dict or set(value) != {'schema', 'candidate_id', 'placement',
            'configuration_digest', 'definition_digest', 'variables_digest', 'reports', 'files', 'digest',
            'last_generated_before', 'last_generated_after'}
            or value['schema'] != SCHEMA or value['candidate_id'] != candidate_id
            or value['digest'] != expected_digest
            or digest({key: item for key, item in value.items() if key != 'digest'}) != expected_digest):
        raise ValueError('Runtime candidate identity differs')
    visible = _fold(value['reports'], candidate_id=candidate_id)
    if value['files'] != {path: entry['file'] for path, entry in visible.items()}:
        raise ValueError('Runtime candidate final file manifest differs')
    if _roster(directory) != {MANIFEST, *value['files']}:
        raise ValueError('Runtime candidate surviving file roster differs')
    for path, receipt in value['files'].items():
        if _file(directory, path) != receipt:
            raise ValueError('Runtime candidate file/member bytes differ')
    return value


def catalog_changes(previous, candidate):
    """Fold verified metadata only; the publication transaction owns activation.

    Earlier catalogue entries retain their original candidate custody. Logical
    deletion removes visibility, never the prior immutable file or its receipt.
    """
    if (type(previous) is not dict or type(candidate) is not dict
            or candidate.get('schema') != SCHEMA
            or candidate.get('digest') != digest({k:v for k,v in candidate.items() if k != 'digest'})):
        raise ValueError('Verified prior catalogue and candidate required')
    aliases = {}
    paths = list(previous)
    for report in candidate['reports']:
        paths.extend(report['remove'])
        paths.extend(value['relative_path'] for value in report['write'])
    for path in paths:
        if type(path) is not str:
            raise ValueError('Explicit catalogue path required')
        folded = path.lower()
        if folded in aliases and aliases[folded] != path:
            raise ValueError('Cross-candidate path-case alias requires qualification')
        aliases[folded] = path
    return _fold(candidate['reports'], previous, candidate_id=candidate['candidate_id'])
