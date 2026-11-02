"""Finite, locked inspection of supported controls outside the profile.

No source aliases, defaults, settings activation or state projection are granted
here. Paths include the actual source row ordinal, including gaps left by
excluded runtime/seed rows. Scalar tags are retained; business parsers remain
with their existing consumers. Validation authenticates the finite cell format,
not a live database owner or the completeness of an absent source.
"""
from dataclasses import dataclass
import re

from mta.row_sequences import is_record_rows
from mta.runtime.execution_setting_values import SettingCell, encode_scalar

OWNER_PREFIX = '/owners'
FORMAT = 'execution-setting-outside-owners-v1'


@dataclass(frozen=True)
class OwnerDescriptor:
    source: tuple
    module: str
    table: str
    fields: tuple
    parameters: tuple
    singleton: bool = False


IMPORTER_PARAMETERS = ('NMSActive', 'DBMActive', 'TaskStatusLogHorizon')
DBM_PARAMETERS = ('FNC_MatchMasterNorm', 'SpikeRuleHorizon', 'SpikeRuleParCount',
                  'NormZeroOneRuleActive', 'DelistingofNormRuleActive')
EFFECTS = {
    'NMSActive': 'Select NMS master/Norm refresh; consumer-specific count and cast rules.',
    'DBMActive': 'Select the existing DBM master refresh behavior.',
    'TaskStatusLogHorizon': 'Retain MDM task-status history using the captured singleton horizon.',
    'FNC_MatchMasterNorm': 'Derive forced-Norm master matching from the exact COUNT=1 source predicate.',
    'SpikeRuleHorizon': 'Select the historical window for DBM spike recommendations.',
    'SpikeRuleParCount': 'Select the joined occurrence threshold for DBM spike recommendations.',
    'NormZeroOneRuleActive': 'Select conditional DBM rules using the original COUNT=1 predicate.',
    'DelistingofNormRuleActive': 'Select the existing delisting recommendation rule.',
    'DBMDelistingDataPointPercent': 'Provide the existing delisting data-point percentage.',
    'SuperDelayFactor': 'Provide the transit factor subject to captured Importer-owner agreement.',
    'ReplenishmentPercentage': 'Provide the first-replenishment introduction release percentage.',
}
DESCRIPTORS = (
    OwnerDescriptor(('importer_settings',), 'Importer/ImporterSettingsTbl',
                    'Importer/ImporterSettingsTbl', ('Parameter', 'Value'), IMPORTER_PARAMETERS),
    OwnerDescriptor(('controls', 'importer_settings'), 'Importer/ImporterSettingsTbl',
                    'Importer/ImporterSettingsTbl', ('Parameter', 'Value'), IMPORTER_PARAMETERS),
    OwnerDescriptor(('controls', 'dbm_settings'), 'DBM/DBMSettingsTbl',
                    'DBM/DBMSettingsTbl', ('Parameter', 'Value'), DBM_PARAMETERS),
    OwnerDescriptor(('dbm', 'DBMSettingsTbl'), 'DBM/DBMSettingsTbl',
                    'DBM/DBMSettingsTbl', ('Parameter', 'Value'), DBM_PARAMETERS),
    # The logical DBM carry has Importer/VFSettings physical storage. This is
    # deliberately distinct from the profile's captured Importer projection.
    OwnerDescriptor(('dbm', 'VFSettings'), 'DBM/VFSettings', 'Importer/VFSettings',
                    ('Parameter', 'Value', 'Description'),
                    ('DBMDelistingDataPointPercent', 'SuperDelayFactor')),
    OwnerDescriptor(('dbm', 'FirstReplenishmentPercentageTbl'), 'DBM/FirstReplenishmentPercentageTbl',
                    'DBM/FirstReplenishmentPercentageTbl', ('ReplenishmentPercentage',),
                    ('ReplenishmentPercentage',), True),
)


def _root(descriptor):
    return OWNER_PREFIX + '/' + '/'.join(descriptor.source)


def _rows(state, descriptor):
    current = state
    for key in descriptor.source:
        if not isinstance(current, dict):
            raise ValueError('Outside settings source container differs: ' + _root(descriptor))
        if key not in current:
            return None
        current = current[key]
    if not is_record_rows(current):
        raise ValueError('Outside settings source must retain ordered record rows: ' + _root(descriptor))
    if descriptor.singleton and len(current) != 1:
        raise ValueError('First replenishment source requires one explicit row')
    return current


def extract(state):
    """Inspect only declared present bags, preserving complete selected rows."""
    if not isinstance(state, dict):
        raise ValueError('Outside settings state must be a dictionary')
    cells = []
    for descriptor in DESCRIPTORS:
        rows = _rows(state, descriptor)
        if rows is None:
            continue
        for ordinal, row in enumerate(rows):
            if not isinstance(row, dict) or set(row) != set(descriptor.fields):
                raise ValueError('Outside settings source row fields differ: ' + _root(descriptor))
            # Validate shape/scalars even for excluded runtime/seed rows; no
            # field normalization or payload acceptance is hidden by filtering.
            for value in row.values():
                encode_scalar(value)
            parameter = descriptor.parameters[0] if descriptor.singleton else row['Parameter']
            if parameter is not None and type(parameter) is not str:
                raise ValueError('Outside settings parameter must be text or NULL')
            if parameter not in descriptor.parameters:
                continue
            for field, value in row.items():
                cells.append(SettingCell.from_value(
                    _root(descriptor) + '/' + str(ordinal) + '/' + field,
                    descriptor.module, parameter, ordinal, value))
    return validate(cells)


def validate(cells):
    """Validate sealed cell identities/whole selected rows without live reads.

    Missing source roots and ordinal gaps are legitimate. This cannot certify
    whether a live source omitted an entire row; admission owns that proof.
    """
    result, seen, rows = [], set(), {}
    for cell in cells:
        if type(cell) is not SettingCell:
            raise ValueError('Outside settings require validated SettingCell records')
        # Reconstruct to retain strict canonical scalar/state checks even if an
        # internal caller has bypassed frozen-dataclass construction safeguards.
        SettingCell.from_dict(cell.as_dict())
        selected = None
        for descriptor in DESCRIPTORS:
            prefix = _root(descriptor) + '/'
            if cell.path.startswith(prefix):
                suffix = cell.path[len(prefix):].split('/')
                if (len(suffix) == 2 and re.fullmatch(r'0|[1-9][0-9]*', suffix[0])
                        and int(suffix[0]) == cell.ordinal and suffix[1] in descriptor.fields):
                    selected = descriptor, suffix[1]
                break
        if selected is None:
            raise ValueError('Unknown outside settings owner/path/field/ordinal')
        descriptor, field = selected
        if (cell.module != descriptor.module or cell.parameter not in descriptor.parameters
                or cell.value_state == 'ABSENT' or descriptor.singleton and cell.ordinal != 0):
            raise ValueError('Outside settings identity/state differs')
        if cell.path in seen:
            raise ValueError('Duplicate outside settings field occurrence')
        seen.add(cell.path)
        group = (_root(descriptor), cell.ordinal)
        row = rows.setdefault(group, {})
        if row and next(iter(row.values())).parameter != cell.parameter:
            raise ValueError('Outside settings row parameter identities differ')
        if field == 'Parameter' and (cell.value_kind != 'text' or cell.value() != cell.parameter):
            raise ValueError('Outside settings Parameter field differs from identity')
        row[field] = cell
        result.append(cell)
    for (root, _), row in rows.items():
        descriptor = next(item for item in DESCRIPTORS if _root(item) == root)
        if set(row) != set(descriptor.fields):
            raise ValueError('Incomplete outside settings selected row')
    return tuple(result)


def describe(state):
    """Finite code-owned metadata; every outside value remains read-only."""
    result = []
    for cell in extract(state):
        descriptor = next(item for item in DESCRIPTORS if cell.path.startswith(_root(item) + '/'))
        result.append(dict(path=cell.path, module=cell.module, parameter=cell.parameter,
            ordinal=cell.ordinal, source='/'.join(descriptor.source), table=descriptor.table,
            field=cell.path.rsplit('/', 1)[-1], activation='OWNER_TRANSITION_LOCKED',
            mutable=False, effect=EFFECTS[cell.parameter]))
    return tuple(result)
