"""Locked outside-setting projections over an operation's existing state.

Source authentication and snapshot selection belong to admission. This adapter
never aliases owners, restores cleared bags, mutates the management version or
changes a consumer's count/conversion rules. Only small declared setting bags
are visited; unrelated masters/history remain shared.
"""
from mta.row_sequences import RecordRows, is_record_rows
from mta.runtime.execution_setting_owners import DESCRIPTORS, OWNER_PREFIX, parameter_name, validate
from mta.runtime.execution_setting_values import SettingCell, encode_scalar, set_path


def expected_owner_rows(cells):
    """Return trusted source tuples mapped to exact rows in frozen ordinal order.

    Accept a combined profile/owner snapshot; non-owner cells belong to the
    separate profile validator. Absent owner cells yield no inferred sources.
    Returned dictionaries are fresh small values, never live owner references.
    """
    selected = []
    for cell in (() if cells is None else cells):
        if type(cell) is not SettingCell:
            raise ValueError('Settings projection requires SettingCell records')
        if cell.path == OWNER_PREFIX or cell.path.startswith(OWNER_PREFIX + '/'):
            selected.append(cell)
    grouped = {}
    for cell in validate(selected):
        root, _, field = cell.path.rpartition('/')
        source_root, _, ordinal = root.rpartition('/')
        descriptor = next(item for item in DESCRIPTORS
                          if source_root == OWNER_PREFIX + '/' + '/'.join(item.source))
        grouped.setdefault(descriptor.source, {}).setdefault(int(ordinal), {})[field] = cell.value()
    return {source: tuple(rows[ordinal] for ordinal in sorted(rows)) for source, rows in grouped.items()}


def _lookup(state, source):
    current = state
    for field in source:
        if not isinstance(current, dict):
            raise ValueError('Settings projection source container differs')
        if field not in current:
            return None
        current = current[field]
    if not is_record_rows(current):
        raise ValueError('Settings projection requires ordered native setting rows')
    return current


def _same(left, right):
    return (set(left) == set(right)
            and all(encode_scalar(left[field]) == encode_scalar(right[field]) for field in left))


def project_state(state, cells):
    """Feed fixed central values into present matching rows using shallow COW.

    Fixed values must already match exactly. Runtime/unknown rows retain their
    order and values. TaskStatusLogHorizon may be wholly omitted by the legacy
    closing owner; its separately captured MDM configuration owns recovery.
    Missing/empty source bags remain missing/empty, never refilled.
    """
    expected = expected_owner_rows(cells)
    if not expected:
        return state  # Historical/no-owner snapshots do not inspect any state.
    if not isinstance(state, dict):
        raise ValueError('Settings projection state must be a dictionary')
    effective = state
    for descriptor in DESCRIPTORS:
        frozen = expected.get(descriptor.source)
        if frozen is None:
            continue
        current = _lookup(state, descriptor.source)
        if current is None or len(current) == 0:
            continue
        if descriptor.singleton and len(current) != 1:
            raise ValueError('Settings projection singleton source differs')
        rows = []
        selected = []
        for row in current:
            if not isinstance(row, dict) or set(row) != set(descriptor.fields):
                raise ValueError('Settings projection source fields differ')
            for value in row.values():
                encode_scalar(value)
            parameter = descriptor.parameters[0] if descriptor.singleton else row['Parameter']
            if parameter is not None and type(parameter) is not str:
                raise ValueError('Settings projection source parameter must be text or NULL')
            if parameter_name(descriptor,parameter) is not None:
                selected.append((len(rows), parameter, row))
            rows.append(row)
        parameters = [parameter for _, parameter, _ in selected]
        frozen_rows = frozen
        if not descriptor.singleton and 'TaskStatusLogHorizon' in descriptor.parameters:
            if 'TaskStatusLogHorizon' not in parameters:
                frozen_rows = tuple(row for row in frozen if row['Parameter'] != 'TaskStatusLogHorizon')
        frozen_parameters = ([descriptor.parameters[0]] * len(frozen_rows) if descriptor.singleton
                             else [row['Parameter'] for row in frozen_rows])
        if parameters != frozen_parameters:
            raise ValueError('Settings projection parameter occurrence sequence differs: ' + '/'.join(descriptor.source))
        for (position, _, row), central in zip(selected, frozen_rows):
            if not _same(row, central):
                raise ValueError('Fixed central setting conflicts with current source: ' + '/'.join(descriptor.source))
            rows[position] = dict(central)
        if not selected:
            continue
        if isinstance(current, RecordRows):
            sealed = tuple(rows)
            replacement = RecordRows(len(sealed), lambda sealed=sealed: iter(sealed),
                                     getitem=lambda ordinal, sealed=sealed: sealed[ordinal])
        else:
            replacement = rows
        effective = set_path(effective, descriptor.source, replacement)
    return effective
