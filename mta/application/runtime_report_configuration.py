"""Native report definitions and placement planning, without execution authority.

This component preserves configuration from RuntimeReports and the independent
DownloadableUIReportSettings table. Validation does not qualify a query,
template, destination, file, database owner or application view. Existing TEST
declarations and runtime admission remain separate and unchanged.
"""
from copy import deepcopy
import hashlib
import json
import re

from mta.domain.complete_daily_scalars import ascii_equal
from mta.serialization import digest

SCHEMA = 'fresh-production-report-configuration-v1'
REFERENCE = 'fresh-production-report-configuration-reference-v1'
LIMIT = 1024 * 1024
PLACEMENTS = ('PostImporter', 'PostBPR', 'PostDBM', 'PostBTR', 'Final')
# A continuation starts after the reports already owned by its accepted cut.
SCOPE_PLACEMENTS = {
    'Full': PLACEMENTS,
    'UptoBPR': PLACEMENTS[:2],
    'PostBPR': PLACEMENTS[2:],
    'UptoDBM': PLACEMENTS[:3],
    'PostDBM': PLACEMENTS[3:],
}
# Literal deployed BPR_DBCreation.sql column names, widths and NULL contracts.
TEXT_FIELDS = {
    'ReportName': (50, False), 'Query': (None, False),
    'BaseDB': (50, False), 'HeaderList': (None, True),
    'FileName': (500, False), 'DestFolder': (500, False),
    'Extension': (10, False), 'Delimeter': (10, True),
    'TemplateName': (50, True), 'TemplateLoc': (500, True),
    'Placement': (50, False), 'LastGeneratedFileName': (500, True),
}
BIT_FIELDS = ('Compression', 'DeleteOldFile', 'Active')
UI_TEXT_FIELDS = {
    'ReportName': (100, False), 'GenerationScope': (50, True),
    'DestFolder': (100, False),
}


def _text(value, contract, label):
    width, nullable = contract
    if value is None and nullable:
        return
    if type(value) is not str or '\0' in value:
        raise ValueError('Native report text required: ' + label)
    try:
        units = len(value.encode('utf-16-le')) // 2
    except UnicodeEncodeError as error:
        raise ValueError('Native report text encoding differs: ' + label) from error
    if width is not None and units > width:
        raise ValueError('Native report text width exceeded: ' + label)


def _bit(value, label, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) not in (bool, int) or value not in (0, 1):
        raise ValueError('Native report bit required: ' + label)


def _placement(value):
    return value is not None and any(ascii_equal(value, name) for name in PLACEMENTS)


def configuration(value):
    """Validate complete native tables; retain spelling, order and scalar types.

    Missing is not an empty declaration. An explicit empty table is representable
    but is not permission to use an empty production roster. Active rows outside
    the five supported pipeline placements are denied rather than ignored.
    """
    if (type(value) is not dict or set(value) != {
            'schema', 'RuntimeReports', 'DownloadableUIReportSettings'}
            or value['schema'] != SCHEMA):
        raise ValueError('Complete production report configuration required')
    runtime = value['RuntimeReports']
    ui = value['DownloadableUIReportSettings']
    if type(runtime) is not list or type(ui) is not list:
        raise ValueError('Explicit native report configuration tables required')
    ids = set()
    for row in runtime:
        if type(row) is not dict or set(row) != {'Id', *TEXT_FIELDS, *BIT_FIELDS}:
            raise ValueError('RuntimeReports column roster differs')
        identity = row['Id']
        if type(identity) is not int or not -2**31 <= identity < 2**31 or identity in ids:
            raise ValueError('Unique native RuntimeReports int Id required')
        ids.add(identity)
        for field, contract in TEXT_FIELDS.items():
            _text(row[field], contract, 'RuntimeReports/' + field)
        for field in BIT_FIELDS:
            _bit(row[field], 'RuntimeReports/' + field)
        if row['Active'] and not _placement(row['Placement']):
            raise ValueError('Active RuntimeReports placement is unsupported')
    names = []
    for row in ui:
        if type(row) is not dict or set(row) != {'Active', *UI_TEXT_FIELDS}:
            raise ValueError('DownloadableUIReportSettings column roster differs')
        for field, contract in UI_TEXT_FIELDS.items():
            _text(row[field], contract, 'DownloadableUIReportSettings/' + field)
        # The existing qualified SQL identifier comparison is CI with space pads.
        # Do not silently substitute Python Unicode equality for the native PK.
        name = row['ReportName']
        if not name.isascii() or any(ascii_equal(name, prior) for prior in names):
            raise ValueError('Unique qualified DownloadableUIReportSettings name required')
        names.append(name)
        _bit(row['Active'], 'DownloadableUIReportSettings/Active', nullable=True)
        if row['Active'] and not _placement(row['GenerationScope']):
            raise ValueError('Active downloadable UI report placement is unsupported')
    if len(json.dumps(value, ensure_ascii=True, allow_nan=False).encode()) > LIMIT:
        raise ValueError('Bounded production report configuration exceeded')
    return deepcopy(value)


def definition_digest(value):
    """LastGeneratedFileName is mutable file state, not a report definition."""
    checked = configuration(value)
    for row in checked['RuntimeReports']:
        del row['LastGeneratedFileName']
    return digest(checked)


def last_generated(value):
    checked = configuration(value)
    return [dict(Id=row['Id'], LastGeneratedFileName=row['LastGeneratedFileName'])
            for row in checked['RuntimeReports']]


def plan(value, scope):
    """Select existing stage owners; no SQL, file generation or READY claim.

    Runtime rows follow the wrapper's ORDER BY Id. UI settings retain supplied
    occurrence order: the independent wrapper has no ORDER BY. Callers must
    qualify that order if more than one applicable UI producer is supported.
    """
    checked = configuration(value)
    if type(scope) is not str or scope not in SCOPE_PLACEMENTS:
        raise ValueError('Explicit supported report execution scope required')
    runtime = sorted(checked['RuntimeReports'], key=lambda row: row['Id'])
    ui = checked['DownloadableUIReportSettings']
    return [dict(placement=placement,
        RuntimeReports=[row for row in runtime
            if row['Active'] and ascii_equal(row['Placement'], placement)],
        DownloadableUIReportSettings=[row for row in ui
            if row['Active'] and ascii_equal(row['GenerationScope'], placement)])
        for placement in SCOPE_PLACEMENTS[scope]]


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate production report configuration key')
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError('Nonfinite production report configuration value')


def decode(raw, expected_sha256):
    if (type(expected_sha256) is not str
            or re.fullmatch('[0-9a-f]{64}', expected_sha256) is None
            or type(raw) is not bytes or not 0 < len(raw) <= LIMIT
            or hashlib.sha256(raw).hexdigest() != expected_sha256):
        raise ValueError('Bounded production report configuration bytes differ')
    checked = configuration(json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite))
    return dict(schema=REFERENCE, sha256=expected_sha256, configuration=checked,
                configuration_digest=digest(checked), definition_digest=definition_digest(checked))


def validate_reference(value):
    if (type(value) is not dict or set(value) != {
            'schema', 'sha256', 'configuration', 'configuration_digest', 'definition_digest'}
            or value['schema'] != REFERENCE
            or type(value['sha256']) is not str
            or re.fullmatch('[0-9a-f]{64}', value['sha256']) is None):
        raise ValueError('Complete production report configuration reference required')
    checked = configuration(value['configuration'])
    if (value['configuration_digest'] != digest(checked)
            or value['definition_digest'] != definition_digest(checked)):
        raise ValueError('Production report configuration identity differs')
    return deepcopy(value)
