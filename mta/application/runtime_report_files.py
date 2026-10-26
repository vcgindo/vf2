"""Successful flat RuntimeReports file effects within one caller-owned root.

The placement owner supplies formatter-qualified bytes, captured macro bindings
and the existing verified archive writer. This module neither runs SQL nor
activates reports. LastGeneratedFileName is returned for the caller's phase
transaction; it never mutates a configuration or a prior accepted receipt.
"""
import re

from mta.application import operational_io as files
from mta.application.runtime_report_projection import describe

SOURCE = ('Engine/GenerateRuntimeReports.bat',
          '8e1c83c49dd7c12dad25c153c923caf28b01db03720fe8aa665a3df09a88c7e8')
EXPORT_SOURCE = ('Scripts/Common/ExportRuntimeReport.sql',
                 '87622287f8f2b8032babb6f04e084a4d0906dc96130f770072a2a79f849a4cdb')


def _name(value):
    # Portable native basenames, with no command interpretation or path alias.
    if (type(value) is not str or not value.isascii()
            or not value
            or any(ord(c) < 32 or c in '<>:"/\\|?*%' for c in value)
            or (value and (value in ('.', '..') or value.endswith((' ', '.'))))
            or value.split('.')[0].upper() in {
                'CON', 'PRN', 'AUX', 'NUL',
                *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}):
        raise ValueError('Qualified runtime report basename required')
    return value


def _resolve(value, variables):
    if type(value) is not str:
        raise ValueError('Explicit runtime file text required')
    match = re.fullmatch(r'%([A-Za-z][A-Za-z0-9_]*)%', value)
    if match:
        if match[1] not in variables:
            raise ValueError('Captured runtime file macro binding missing')
        value = variables[match[1]]
    if type(value) is not str or '%' in value:
        raise ValueError('Unsupported runtime file macro expression')
    return value


def layout(definition, variables):
    """Validate the supported successful file branch before any filesystem effect.

    Native destinations are mapped explicitly to caller-owned relative folders;
    no captured absolute legacy path becomes write authority on this platform.
    SQLCMD formatting/delimiter qualification remains the payload producer's job.
    """
    spec = describe(definition)
    required = {'Id', 'FileName', 'LastGeneratedFileName', 'DestFolder',
                'Extension', 'Compression', 'DeleteOldFile', 'TemplateName', 'TemplateLoc'}
    if not required <= definition.keys() or type(variables) is not dict:
        raise ValueError('Complete runtime file definition/bindings required')
    if (type(definition['Id']) is not int or definition['Extension'] != 'csv'
            or definition['TemplateName'] is not None or definition['TemplateLoc'] is not None):
        raise ValueError('Qualified flat CSV RuntimeReports branch required')
    for field in ('Compression', 'DeleteOldFile'):
        if type(definition[field]) not in (bool, int) or definition[field] not in (0, 1):
            raise ValueError('Native runtime file bit required')
    name = _name(_resolve(definition['FileName'], variables))
    # The canonical selector uses ISNULL(...,' '). Native Windows FOR/F retains
    # that one-space token, so a fresh NULL owner cleans " .csv" / " .zip".
    # An empty non-NULL token shifts FOR/F fields and is a different contract.
    previous = (' ' if definition['LastGeneratedFileName'] is None
                else _name(definition['LastGeneratedFileName']))
    destination = _resolve(definition['DestFolder'], variables)
    # The caller maps a native folder to its explicit owned namespace. Ban the
    # staging namespace to prevent a destination copy deleting its own source.
    if (not destination or destination.split('/')[0].lower() == 'output'):
        raise ValueError('Separate owned runtime destination required')
    for component in destination.split('/'):
        _name(component)
    extension = 'zip' if definition['Compression'] else 'csv'
    return dict(report_id=definition['Id'], query_sha256=spec['query_sha256'],
        file_name=name, previous_file_name=previous, destination=destination,
        compression=bool(definition['Compression']), delete_old=bool(definition['DeleteOldFile']),
        csv='output/'+name+'.csv', output='output/'+name+'.'+extension,
        previous_csv='output/'+previous+'.csv', previous_output='output/'+previous+'.'+extension,
        download=destination+'/'+name+'.'+extension,
        previous_download=destination+'/'+previous+'.'+extension)


def publish(*, root, definition, variables, report_bytes=None, report_chunks=None, archive_writer=None):
    """Apply the canonical successful file lifecycle; no readiness assertion.

    A failure raises, leaving unaccepted staging for the placement owner to
    handle. Neither a partial file nor this receipt is a phase acceptance.
    """
    selected = layout(definition, variables)
    if (report_bytes is None) == (report_chunks is None):
        raise ValueError('Exactly one formatter-qualified runtime payload required')
    if report_bytes is not None:
        if type(report_bytes) is not bytes:
            raise ValueError('Explicit formatter-qualified runtime bytes required')
        report_chunks = (report_bytes,)
    elif isinstance(report_chunks, (str, bytes, bytearray)):
        raise ValueError('Explicit runtime byte-chunk iterable required')
    try:
        report_chunks = iter(report_chunks)
    except TypeError as error:
        raise ValueError('Explicit runtime byte-chunk iterable required') from error
    if selected['compression'] and not callable(archive_writer):
        raise ValueError('Verified runtime archive writer required')
    # Validate every path before cleanup, including unused previous names.
    for field in ('csv', 'output', 'previous_csv', 'previous_output', 'download', 'previous_download'):
        files.owned_path(root, selected[field])
    for relative in (selected['previous_csv'], selected['csv']):
        files.remove_file(root, relative)
    csv_receipt = files.write_chunks(root, selected['csv'], report_chunks)
    archive_receipt = None
    if selected['compression']:
        for relative in (selected['previous_output'], selected['output']):
            files.remove_file(root, relative)
        archive_receipt = archive_writer(root=root, staging='output',
            members=[selected['file_name']+'.csv'], destination=selected['output'])
        members = files.zip_members(root, selected['output'])
        expected = [dict(ordinal=0, name=selected['file_name']+'.csv',
                         sha256=csv_receipt['sha256'], size_bytes=csv_receipt['size_bytes'])]
        if members != expected:
            raise ValueError('Runtime archive member bytes/roster differ')
        files.remove_file(root, selected['csv'])
    if selected['delete_old']:
        files.remove_file(root, selected['previous_download'])
    files.remove_file(root, selected['download'])
    output = files.inspect_file(root, selected['output'])
    download = files.copy_file(root, selected['output'], selected['download'])
    return dict(report_id=selected['report_id'], query_sha256=selected['query_sha256'],
                last_generated_file_name=selected['file_name'], output=output,
                download=download, csv=csv_receipt, archive=archive_receipt,
                source_sha256=SOURCE[1], export_source_sha256=EXPORT_SOURCE[1])
