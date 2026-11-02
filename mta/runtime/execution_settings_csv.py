"""Operator-editable values with exact types and optimistic revision checking.

The exported file carries its own row identities/revision. Operators edit only
Value on an editable row; release-owned metadata never grants capability.
"""
import csv
from dataclasses import replace
from io import StringIO
from mta.runtime.execution_setting_catalogue import describe_cells
from mta.runtime.execution_setting_values import SettingCell

COLUMNS = ('Revision', 'Version', 'Module', 'Parameter', 'Occurrence', 'Value', 'Type',
           'State', 'Activation', 'Effect', 'Source', 'Path')


def export_text(version, cells):
    cells = tuple(cells)
    output = StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=COLUMNS, lineterminator='\n')
    writer.writeheader()
    for cell, info in zip(cells, describe_cells(cells)):
        writer.writerow(dict(Revision=version.revision, Version=str(version.pk), Module=cell.module,
            Parameter=cell.parameter, Occurrence=cell.ordinal,
            Value='' if cell.value_text is None else cell.value_text,
            Type=cell.value_kind, State=cell.value_state, Activation=info['activation'],
            Effect=info['description'], Source=info['source_owner'], Path=cell.path))
    return output.getvalue()


def import_text(text, version, cells):
    """Validate the complete export, permitting only a qualified value delta."""
    cells = tuple(cells)
    reader = csv.DictReader(StringIO(text.lstrip('\ufeff'), newline=''))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise ValueError('Settings columns differ; export a new file and edit only Value')
    incoming = list(reader)
    expected = list(csv.DictReader(StringIO(export_text(version, cells), newline='')))
    if len(incoming) != len(expected):
        raise ValueError('Settings rows differ; no row may be omitted or inserted')
    projected = []
    for row, old, cell, info in zip(incoming, expected, cells, describe_cells(cells)):
        if set(row) != set(COLUMNS) or any(row[key] != old[key] for key in COLUMNS if key != 'Value'):
            raise ValueError('Settings identity/type/metadata differs; edit only Value')
        if row['Value'] == old['Value']:
            projected.append(cell)
            continue
        if not info['mutable']:
            raise ValueError('Settings activation is locked: ' + cell.parameter)
        # SettingCell validates canonical lexical form. In particular, NULL,
        # blank text, bool and integer remain distinct; no Excel-style coercion.
        changed = replace(cell, value_text=row['Value'])
        if cell.path == '/delivery/batch/AutoDBMActive' and (
                changed.value_state != 'VALUE' or type(changed.value()) is not int
                or changed.value() not in (0, 1)):
            raise ValueError('AutoDBMActive requires an explicit integer 0/1')
        projected.append(changed)
    return tuple(projected)


def revision(text):
    reader = csv.DictReader(StringIO(text.lstrip('\ufeff'), newline=''))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise ValueError('Unsupported settings file; export it from this installation')
    values = {row.get('Revision') for row in reader}
    if len(values) != 1:
        raise ValueError('Settings file must contain exactly one complete revision')
    value = values.pop()
    if not value or not value.isascii() or not value.isdecimal() or str(int(value)) != value or int(value) < 1:
        raise ValueError('Settings revision is invalid')
    return int(value)
