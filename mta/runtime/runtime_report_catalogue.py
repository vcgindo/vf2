"""Pure reconstruction of RuntimeReports catalogue transitions.

Arguments named configuration, provenance and previous state must come from the
registrar's authenticated readers. This module authenticates neither those
readers nor anchors, and performs no filesystem work. Candidate verification
and the registrar's independent source/file recomputation remain mandatory.
"""
from copy import deepcopy
import json
from pathlib import PurePosixPath
import re
from uuid import UUID

from mta.application.runtime_report_configuration import configuration, definition_digest, plan
from mta.application.runtime_report_files import layout, _name
from mta.runtime import runtime_report_candidates as candidates
from mta.serialization import digest

ANCHOR_SCHEMA = 'fresh-runtime-report-catalogue-anchor-v1'
LIMIT = candidates.LIMIT


def _bounded(value):
    try:
        raw = json.dumps(value, ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError('Finite JSON catalogue metadata required') from error
    if len(raw.encode()) > LIMIT:
        raise ValueError('Catalogue metadata exceeds bound')


def _sha(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('Explicit catalogue SHA256 required')


def _uuid(value):
    try:
        valid = type(value) is str and str(UUID(value)) == value
    except (ValueError, AttributeError):
        valid = False
    if not valid:
        raise ValueError('Canonical catalogue custody UUID required')


def _path(value):
    if (type(value) is not str or not value or '\\' in value or ':' in value
            or PurePosixPath(value).is_absolute() or str(PurePosixPath(value)) != value):
        raise ValueError('Canonical relative catalogue path required')
    for part in value.split('/'):
        _name(part)


def _file(value, path):
    if (type(value) is not dict or set(value) != {'relative_path', 'sha256', 'size_bytes', 'members'}
            or value['relative_path'] != path or type(value['size_bytes']) is not int
            or value['size_bytes'] < 0 or type(value['members']) is not list):
        raise ValueError('Complete catalogue file custody required')
    _path(path)
    _sha(value['sha256'])
    if not path.lower().endswith('.zip') and value['members']:
        raise ValueError('Nonarchive catalogue members differ')
    for ordinal, member in enumerate(value['members']):
        if (type(member) is not dict or set(member) != {'ordinal', 'name', 'sha256', 'size_bytes'}
                or type(member['ordinal']) is not int or member['ordinal'] != ordinal
                or type(member['size_bytes']) is not int or member['size_bytes'] < 0):
            raise ValueError('Complete ordered catalogue archive member required')
        _name(member['name'])
        _sha(member['sha256'])


def validate_catalogue(value):
    """Validate explicit finite custody metadata, without authenticating bytes."""
    if type(value) is not dict:
        raise ValueError('Explicit prior catalogue required; missing is unavailable')
    _bounded(value)
    aliases = {}
    for path, entry in value.items():
        _path(path)
        if path.lower() in aliases and aliases[path.lower()] != path:
            raise ValueError('Prior catalogue path-case alias requires qualification')
        aliases[path.lower()] = path
        if type(entry) is not dict or set(entry) != {'candidate_id', 'file'}:
            raise ValueError('Complete prior catalogue custody required')
        _uuid(entry['candidate_id'])
        _file(entry['file'], path)
    return deepcopy(value)


def _names(value, checked):
    if (type(value) is not list or any(type(row) is not dict
            or set(row) != {'Id', 'LastGeneratedFileName'} or type(row['Id']) is not int
            for row in value)):
        raise ValueError('Explicit generated filename state required')
    names = {row['Id']: row['LastGeneratedFileName'] for row in value}
    if len(names) != len(value) or set(names) != {row['Id'] for row in checked['RuntimeReports']}:
        raise ValueError('Generated filename state roster differs')
    # Preserve the native nullable nvarchar contract for inactive rows too.
    # Basename qualification belongs to layout for rows actually executed;
    # inactive legacy text must not acquire a new file-path meaning here.
    effective = deepcopy(checked)
    for row in effective['RuntimeReports']:
        row['LastGeneratedFileName'] = names[row['Id']]
    configuration(effective)
    return names


def reconstruct_events(*, report_configuration, placement, variables, last_generated, provenance):
    """Derive the exact ordered lifecycle from independently trusted arguments.

    Provenance is the registrar-reconstructed per-Id metadata, never the
    candidate's own source bag. Byte hashes are intentionally absent here.
    """
    checked = configuration(report_configuration)
    _bounded(variables)
    if type(variables) is not dict:
        raise ValueError('Explicit captured runtime variables required')
    names = _names(last_generated, checked)
    effective = deepcopy(checked)
    for row in effective['RuntimeReports']:
        row['LastGeneratedFileName'] = names[row['Id']]
    stages = [stage for stage in plan(effective, 'Full') if stage['placement'] == placement]
    if len(stages) != 1 or stages[0]['DownloadableUIReportSettings']:
        raise ValueError('Explicit RuntimeReports-only placement required')
    definitions = stages[0]['RuntimeReports']
    if (type(provenance) is not dict or any(type(key) is not int for key in provenance)
            or set(provenance) != {row['Id'] for row in definitions}):
        raise ValueError('Exact trusted report provenance roster required')
    _bounded(provenance)
    events = []
    for row in definitions:
        selected = layout(row, variables)
        source = provenance[row['Id']]
        if type(source) is not dict or source.get('query_sha256') != selected['query_sha256']:
            raise ValueError('Trusted report provenance query differs')
        removals = [selected['previous_csv'], selected['csv']]
        if selected['compression']:
            removals += [selected['previous_output'], selected['output']]
        if selected['delete_old']:
            removals.append(selected['previous_download'])
        removals.append(selected['download'])
        events.append(dict(report_id=row['Id'],
            definition_digest=digest({key: value for key, value in row.items()
                                      if key != 'LastGeneratedFileName'}),
            source=deepcopy(source), last_generated_file_name=selected['file_name'],
            remove=list(dict.fromkeys(removals)),
            write=[selected['output'], selected['download']], layout=selected))
        names[row['Id']] = selected['file_name']
    return dict(configuration_digest=digest(checked), definition_digest=definition_digest(checked),
        variables_digest=digest(variables), events=events,
        last_generated_before=deepcopy(last_generated),
        last_generated_after=[dict(Id=row['Id'], LastGeneratedFileName=names[row['Id']])
                              for row in last_generated])


def validate_candidate(*, candidate, report_configuration, placement, variables,
                       last_generated, provenance, previous_catalogue):
    """Compare verified candidate metadata to authority and fold file custody.

    Does not reread or regenerate files. Call only in addition to candidate
    filesystem verification and registrar source-to-content recomputation.
    """
    previous = validate_catalogue(previous_catalogue)
    expected = reconstruct_events(report_configuration=report_configuration, placement=placement,
        variables=variables, last_generated=last_generated, provenance=provenance)
    _bounded(candidate)
    if (type(candidate) is not dict or set(candidate) != {'schema', 'candidate_id', 'placement',
            'configuration_digest', 'definition_digest', 'variables_digest', 'reports', 'files',
            'digest', 'last_generated_before', 'last_generated_after'}
            or candidate['schema'] != candidates.SCHEMA or candidate['placement'] != placement
            or type(candidate['reports']) is not list or type(candidate['files']) is not dict):
        raise ValueError('Complete placement candidate required')
    _uuid(candidate['candidate_id'])
    if candidate['digest'] != digest({key: value for key, value in candidate.items() if key != 'digest'}):
        raise ValueError('Candidate metadata digest differs')
    for key in ('configuration_digest', 'definition_digest', 'variables_digest',
                'last_generated_before', 'last_generated_after'):
        if digest(candidate[key]) != digest(expected[key]):
            raise ValueError('Candidate authoritative '+key+' differs')
    if len(candidate['reports']) != len(expected['events']):
        raise ValueError('Candidate authoritative report roster differs')
    for actual, event in zip(candidate['reports'], expected['events']):
        if (type(actual) is not dict or set(actual) != {'report_id', 'definition_digest', 'source',
                'last_generated_file_name', 'remove', 'write'} or type(actual['write']) is not list):
            raise ValueError('Candidate report event shape differs')
        for key in ('report_id', 'definition_digest', 'source', 'last_generated_file_name', 'remove'):
            if digest(actual[key]) != digest(event[key]):
                raise ValueError('Candidate authoritative report '+key+' differs')
        if len(actual['write']) != len(event['write']):
            raise ValueError('Candidate authoritative write roster differs')
        for value, path in zip(actual['write'], event['write']):
            _file(value, path)
    # Reuse the existing canonical fold after independent event validation.
    visible = candidates.catalog_changes({}, candidate)
    if digest(candidate['files']) != digest({path: entry['file'] for path, entry in visible.items()}):
        raise ValueError('Candidate surviving file manifest differs')
    catalogue = candidates.catalog_changes(previous, candidate)
    return dict(catalogue=catalogue, last_generated=expected['last_generated_after'],
                events=expected['events'])


def validate_anchor(value, *, report_configuration):
    """Check a bounded anchor *shape*, never establish historical authority.

    The registrar must independently authenticate retained evidence, identity,
    configuration, custody and names. A self-consistent hash is not evidence.
    INITIALIZATION identifies the installation, PRE_FEATURE the old run. Neither
    creates an old publication receipt nor makes other report families empty.
    """
    _bounded(value)
    if (type(value) is not dict or set(value) != {'schema', 'kind', 'identity', 'output_digest',
            'configuration_digest', 'definition_digest', 'catalogue', 'last_generated', 'evidence'}
            or value['schema'] != ANCHOR_SCHEMA or value['kind'] not in ('PRE_FEATURE', 'INITIALIZATION')):
        raise ValueError('Explicit versioned catalogue anchor required')
    _uuid(value['identity'])
    if value['kind'] == 'PRE_FEATURE':
        _sha(value['output_digest'])
    elif value['output_digest'] is not None:
        raise ValueError('Initialization anchor cannot claim an old output')
    checked = configuration(report_configuration)
    if (value['configuration_digest'] != digest(checked)
            or value['definition_digest'] != definition_digest(checked)):
        raise ValueError('Anchor configuration differs')
    validate_catalogue(value['catalogue'])
    _names(value['last_generated'], checked)
    evidence = value['evidence']
    if type(evidence) is not dict or not 1 <= len(evidence) <= 32:
        raise ValueError('Explicit bounded anchor evidence references required')
    for name, identity in evidence.items():
        if type(name) is not str or re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,63}', name) is None:
            raise ValueError('Finite anchor evidence name required')
        _sha(identity)
    return deepcopy(value)
