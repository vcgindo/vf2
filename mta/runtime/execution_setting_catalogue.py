"""Finite profile scalar catalogue and lossless, explicitly bounded projection.

Only AutoDBMActive is mutable in this release. Other admitted controls are
visible but locked until their activation prerequisites are proved. Masters,
facts, code memberships, logistics, policies and operational state retain their
existing owners. This adapter neither validates a whole initialization nor
grants admission. Paths are JSON pointers for identity/display; projection uses
addresses derived from the trusted original profile, never parsed user paths.
"""
from dataclasses import dataclass

from mta.row_sequences import is_record_rows
from mta.runtime.execution_setting_values import SettingCell


AUTO_DBM_PATH = ('delivery', 'batch', 'AutoDBMActive')
AUTO_DBM_CELL_PATH = '/delivery/batch/AutoDBMActive'
FORMAT = 'execution-setting-profile-catalogue-v1'


@dataclass(frozen=True)
class _Root:
    path: tuple
    module: str
    keys: tuple | None = None
    bag: bool = False
    activation: str = 'TRANSITION_LOCKED'


BATCH_KEYS = (
    'AutoDBMActive', 'DBMNormChangeReportHorizon', 'NormChangeLogHorizon',
    'GatherSuspensionHistory', 'ActivateNormChangeLogReport',
    'DailyConsumptionHorizonDBM', 'PhaseOutRecommendation30Days',
    'PhaseOutRecommendation60Days', 'PhaseOutRecommendation90Days',
    'ActivateNorm0Report30Days', 'ActivateNorm0Report60Days',
    'ActivateNorm0Report90Days', 'ActivateNorm1Report30Days', 'ActivateNorm2Report30Days',
    'Norm1Increase_MultipleRLT', 'Norm2Decrease_MultipleRLT',
    'PhaseOutRecommendationTolerance30Days', 'PhaseOutRecommendationTolerance60Days',
    'PhaseOutRecommendationTolerance90Days',
)
ROOTS = (
    _Root(('import_non_nms',), 'Importer'),
    _Root(('daily', 'settings'), 'Importer', ('Parameter', 'Value'), True),
    _Root(('daily', 'vf_settings'), 'Importer', ('Parameter', 'Value'), True),
    _Root(('daily', 'shell_flags'), 'Modules',
          ('DistributorSystemActive', 'VendorSystemActive', 'VectorDMSActive')),
    _Root(('calculation', 'stock_configuration'), 'BPR',
          ('reservation_type', 'reservation_for_rationing_only')),
    _Root(('calculation', 'allocation'), 'BPR', ('advance_stock_threshold_percent',)),
    _Root(('force_flags',), 'NormControls',
          ('from_ui', 'ignore_master_norm', 'nms_active'), activation='DERIVED_OR_FIXED'),
    _Root(('delivery', 'site_code'), 'Delivery', activation='FIXED_REFERENCE'),
    _Root(('delivery', 'batch'), 'DBM', BATCH_KEYS),
    _Root(('delivery', 'controls'), 'NormControls', ('from_ui', 'start_percent', 'history_horizon')),
    _Root(('delivery', 'btr_settings'), 'BTR',
          ('CaptureDispatchExecutionEfficiency', 'GenerateColorAgeingReport',
           'BRAgeColorTolerance', 'CARNoColorToleranceDuration',
           'NormSuggestion_Upward', 'NormSuggestion_Downward', 'RationingHistoryHorizonBTR')),
    _Root(('delivery', 'conditional_dbm', 'importer_vf_settings'), 'ImporterVFSettings',
          ('Parameter', 'Value', 'Description'), True),
    _Root(('delivery', 'btr_history', 'importer_vf_settings'), 'ImporterVFSettings',
          ('Parameter', 'Value', 'Description'), True),
    _Root(('complete_daily',), 'Finalization', ('policy', 'consumption_days', 'remark_days')),
    _Root(('complete_pick',), 'Pick', ('policy',), activation='FIXED_REFERENCE'),
    _Root(('daily_publication',), 'Publication', activation='FIXED_REFERENCE'),
    _Root(('daily_publication_config',), 'Publication', ('bpr_remark_horizon',)),
    _Root(('native_upload_audit',), 'UploadAudit', ('horizon', 'timezone', 'client_folder')),
    *(_Root((name,), 'Policy', activation='FIXED_REFERENCE') for name in
      ('operational_sources', 'operational_force_sources', 'operational_input_sources',
       'synthetic_action_policy')),
)

EXCLUSIONS = (
    'calculation.skus/locations/stock_openings/policies/logistics/replenishment_exclusions: '
    'typed master, attribute, fact and source populations',
    'daily.distributor_codes/vendor_codes/vector_dms_codes/module_sources: '
    'owned membership and module source populations',
    'opening/state and persisted ImporterSettingsTbl/DBMSettingsTbl/VFSettings: '
    'independent state owners, not profile subtrees',
    'OperationalConfiguration and registered report definitions: separate immutable owners',
)


def _pointer(address):
    return '/' + '/'.join(str(part).replace('~', '~0').replace('/', '~1') for part in address)


def _selected(profile):
    """Yield cells and trusted addresses without traversing excluded branches."""
    if type(profile) is not dict:
        raise ValueError('Original settings profile must be a dictionary')
    for root in ROOTS:
        current = profile
        for key in root.path:
            if type(current) is not dict:
                raise ValueError('Settings profile container differs: ' + _pointer(root.path))
            if key not in current:
                break
            current = current[key]
        else:
            if root.bag:
                if not is_record_rows(current):
                    raise ValueError('Settings source must retain its ordered row list')
                for ordinal, row in enumerate(current):
                    if not isinstance(row, dict) or set(row) != set(root.keys) or type(row['Parameter']) is not str:
                        raise ValueError('Settings source row fields differ: ' + _pointer(root.path))
                    for key, value in row.items():
                        address = (*root.path, ordinal, key)
                        yield SettingCell.from_value(_pointer(address), root.module,
                                                     row['Parameter'], ordinal, value), address, root
            elif root.keys is not None:
                if type(current) is not dict or set(current) - set(root.keys):
                    raise ValueError('Undeclared settings scalar fields: ' + _pointer(root.path))
                for key, value in current.items():
                    address = (*root.path, key)
                    if address == AUTO_DBM_PATH and (type(value) is not int or value not in (0, 1)):
                        raise ValueError('Original AutoDBMActive requires an explicit integer 0/1')
                    yield SettingCell.from_value(_pointer(address), root.module, key, 0, value), address, root
            else:
                yield SettingCell.from_value(_pointer(root.path), root.module,
                                             root.path[-1], 0, current), root.path, root


def extract(profile):
    """Return exact present scalar cells; omitted optional fields stay omitted."""
    return tuple(cell for cell, _, _ in _selected(profile))


def describe(profile):
    """Release-owned display metadata; it is never accepted as write authority."""
    result = []
    for cell, address, root in _selected(profile):
        mutable = address == AUTO_DBM_PATH
        result.append(dict(path=cell.path, module=cell.module, parameter=cell.parameter,
            ordinal=cell.ordinal, mutable=mutable,
            activation='FUTURE_RUN' if mutable else root.activation,
            description=('Automatic acceptance of eligible DBM recommendations; strict integer 0/1.'
                         if mutable else 'Exact current owner value; activation remains locked.'),
            source_owner=_pointer(root.path)))
    return tuple(result)


def describe_cells(cells):
    """Describe authenticated version cells without reading large profiles."""
    from mta.runtime.execution_setting_owners import DESCRIPTORS, EFFECTS, OWNER_PREFIX, validate
    cells = tuple(cells)
    validate(cell for cell in cells if cell.path.startswith(OWNER_PREFIX + '/'))
    result = []
    for cell in cells:
        if cell.path.startswith(OWNER_PREFIX + '/'):
            owner = next(item for item in DESCRIPTORS
                         if cell.path.startswith(OWNER_PREFIX + '/' + '/'.join(item.source) + '/'))
            result.append(dict(path=cell.path, module=cell.module, parameter=cell.parameter,
                ordinal=cell.ordinal, mutable=False, activation='OWNER_TRANSITION_LOCKED',
                description=EFFECTS[cell.parameter], source_owner=owner.table + ' / ' + '/'.join(owner.source)))
            continue
        root = next((item for item in ROOTS if cell.path == _pointer(item.path)
                     or cell.path.startswith(_pointer(item.path) + '/')), None)
        if root is None:
            raise ValueError('Unknown settings description path')
        mutable = cell.path == AUTO_DBM_CELL_PATH
        result.append(dict(path=cell.path, module=cell.module, parameter=cell.parameter,
            ordinal=cell.ordinal, mutable=mutable,
            activation='FUTURE_RUN' if mutable else root.activation,
            description=('Automatic acceptance of eligible DBM recommendations; integer 0/1.'
                         if mutable else 'Exact supported owner value; changing it remains locked.'),
            source_owner=_pointer(root.path)))
    return tuple(result)


def _identity(cell):
    return cell.path, cell.module, cell.parameter, cell.ordinal


def _replace(root, address, value):
    # address was obtained exclusively from _selected(original_profile).
    if not address:
        return value
    key, *tail = address
    copied = root.copy()
    copied[key] = _replace(root[key], tail, value)
    return copied


def project(original_profile, cells):
    """Project a complete exact roster, permitting only the qualified delta.

    No defaults, aliases, deduplication or general JSON patching are performed.
    Unchanged profiles and unrelated populations keep their object identities.
    """
    expected = tuple(_selected(original_profile))
    provided = {}
    for cell in cells:
        if type(cell) is not SettingCell:
            raise ValueError('Projection requires validated SettingCell records')
        identity = _identity(cell)
        if identity in provided:
            raise ValueError('Duplicate settings cell identity')
        provided[identity] = cell
    if set(provided) != {_identity(cell) for cell, _, _ in expected}:
        raise ValueError('Settings cell roster or metadata differs from original profile')
    effective = original_profile
    for original, address, _ in expected:
        selected = provided[_identity(original)]
        if selected == original:
            continue
        if address != AUTO_DBM_PATH:
            raise ValueError('Settings activation is locked: ' + original.path)
        value = selected.value()
        if selected.value_state != 'VALUE' or type(value) is not int or value not in (0, 1):
            raise ValueError('AutoDBMActive requires an explicit integer 0/1')
        effective = _replace(effective, address, value)
    return effective
