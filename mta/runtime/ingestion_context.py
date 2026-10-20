"""Bounded identities for preparation; business populations stay with their owners.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from dataclasses import dataclass
from enum import Enum
import re
from uuid import UUID

CONTRACT = 'vectorflow-ingestion-ownership-v1'
BASELINE_RELEASE = '687adcf024ea9bffe0c90b3de2bb67e25019ec4a'
FAMILIES = tuple(range(1, 14))


class DataOwner(str, Enum):
    MASTER = 'master'
    CONFIGURATION = 'configuration'
    FACT = 'fact'
    OPERATIONAL = 'operational'
    ACTION = 'action'


def sha(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('An exact SHA256 identity is required')
    return value


def identity(value):
    if type(value) is not str or str(UUID(value)) != value:
        raise ValueError('A canonical UUID string is required')
    return value


@dataclass(frozen=True)
class RevisionCut:
    master: int
    configuration: int
    fact: int
    operational: int
    action: int

    def __post_init__(self):
        if any(type(v) is not int or v < 0 for v in self.as_tuple()):
            raise ValueError('Revision cut requires nonnegative integer generations')

    def as_tuple(self):
        return (self.master, self.configuration, self.fact, self.operational, self.action)


@dataclass(frozen=True)
class PopulationReference:
    """One direct immutable owner, never a chain of daily delta references."""
    owner: DataOwner
    kind: str
    owner_id: str
    path: str
    schema: str
    count: int
    digest: str

    def __post_init__(self):
        if not isinstance(self.owner, DataOwner) or self.kind not in ('INITIALIZATION', 'RUN', 'BATCH'):
            raise ValueError('Explicit immutable population owner required')
        identity(self.owner_id)
        sha(self.digest)
        if (type(self.count) is not int or self.count < 0 or type(self.path) is not str
                or not re.fullmatch(r'[A-Za-z0-9_/-]{1,240}', self.path)
                or '..' in self.path or '//' in self.path
                or type(self.schema) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}', self.schema)):
            raise ValueError('Population reference shape differs')
        if self.owner in (DataOwner.OPERATIONAL, DataOwner.ACTION) and self.kind == 'INITIALIZATION':
            # Opening operating state is legitimate; the caller must bind it as
            # the first-day predecessor, not disguise it as a static master.
            if not self.path.startswith('input/opening/'):
                raise ValueError('Opening operational state requires its declared opening path')


@dataclass(frozen=True)
class PreparedRunInputs:
    initialization_id: str
    source_digest: str
    certification_digest: str
    master_revision_id: str
    configuration_digest: str
    batch_id: str
    batch_digest: str
    predecessor_id: str | None
    predecessor_digest: str | None
    implementation_digest: str
    revisions: RevisionCut
    populations: tuple[PopulationReference, ...]
    contract: str = CONTRACT

    def __post_init__(self):
        for value in (self.initialization_id, self.master_revision_id, self.batch_id):
            identity(value)
        for value in (self.source_digest, self.certification_digest, self.configuration_digest,
                      self.batch_digest, self.implementation_digest):
            sha(value)
        if self.contract != CONTRACT or not isinstance(self.revisions, RevisionCut):
            raise ValueError('Unsupported preparation ownership contract')
        if (self.predecessor_id is None) != (self.predecessor_digest is None):
            raise ValueError('Predecessor identity and output digest belong together')
        if self.predecessor_id is not None:
            identity(self.predecessor_id)
            sha(self.predecessor_digest)
        if (type(self.populations) is not tuple or len(self.populations) > 512
                or any(not isinstance(p, PopulationReference) for p in self.populations)
                or len({p.path for p in self.populations}) != len(self.populations)):
            raise ValueError('Bounded unique population references required')


# Current schemas contain both static and operational columns. A field named
# Norm must never become static merely because it lives in a master table.
OPERATIONAL_MASTER_FIELDS = frozenset(('Norm', 'NewNorm', 'Status', 'Comment',
    'LastProcessedDate', 'LastRunDate', 'SuspendDate', 'ResumeDate'))
CONFIGURATION_FIELDS = frozenset(('MinNorm', 'RLT', 'RCP', 'GCP', 'OCP', 'PackSize',
    'SpikeThreshold', 'DefaultSpikeThreshold', 'PSOThreshold', 'DefaultPSOThreshold',
    'DBMActive', 'FGRMFlag', 'StockPercentForRationing', 'StockPercentForRat',
    'NormPercentReservation', 'MinOrderCount', 'ElephantOrderCapping', 'NonNMS'))
STATIC_MASTER_FIELDS = frozenset(('id', 'source', 'owner', 'ordinal', 'use_kind', 'SKUCode', 'WhCode',
    'WHCode', 'LocCode', 'ParentWhCode', 'SKUDescription', 'WHDescription', 'ParentDescription',
    'Weight', 'Volume', 'LocationType', 'LogisticsLocation', 'SKUIntroDate',
    *(f'{p}{i}' for p in ('SL', 'LL', 'c') for i in range(1, 16)),
    *(f'{p}{i:02}' for p in ('SKUAtt', 'LocAtt', 'SKULocAtt') for i in range(1, 16))))


def master_field_owner(name):
    if name in OPERATIONAL_MASTER_FIELDS:
        return DataOwner.OPERATIONAL
    if name in CONFIGURATION_FIELDS:
        return DataOwner.CONFIGURATION
    if name in STATIC_MASTER_FIELDS:
        return DataOwner.MASTER
    raise ValueError('Unclassified master field: ' + str(name))
