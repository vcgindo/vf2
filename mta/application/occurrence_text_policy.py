"""Versioned availability of unordered diagnostic text; never numeric parity.

The immutable fact request is unchanged. Native capture admits this separate
run-owned policy, which travels with accepted phases and produced lineage.
"""
from copy import deepcopy
from datetime import date
import re
import uuid

from mta.serialization import digest

KEY = 'occurrence_text_policy'
ID = 'norm012-30-occurrence-availability-v1'
CLASSIFICATION = 'LEGACY_FLAW/NOT_PARITY'
DISPLAY = 'UNAVAILABLE: LEGACY_FLAW/NOT_PARITY - unordered STRING_AGG'
STAGES = {'norm0-export': 0, 'norm1-export': 1, 'norm2-export': 2}
POLICY = dict(id=ID, version=1, norms=[0, 1, 2], horizons=[30], field='Occurances',
    classification=CLASSIFICATION, display=DISPLAY,
    authorization='human-controller-2026-10-30',
    source_sql_sha256={
        '0': 'c47103cd5d309c8d692766fcef798ab138694627d944dee7c3d25619c9ed9766',
        '1': '64c58d14390ce1133ff39ccb7c619827fc7c4e01625188e92f9dfe15ef53e7d2',
        '2': '9edb9e13504f36d6655cb762aa81853cdd10a4e44bba876fee3ffc8c83c16870'})
OWNER_FIELDS = {'run_id', 'business_date', 'input_digest', 'configuration_digest',
                'predecessor_id', 'predecessor_output_digest', 'execution_revision', 'source_commit'}


def binding(owner):
    value = dict(policy=deepcopy(POLICY), owner=deepcopy(owner))
    value['binding_digest'] = digest(value)
    return require_binding(value)


def require_binding(value, *, norm=None, horizon=None):
    if (type(value) is not dict or set(value) != {'policy', 'owner', 'binding_digest'}
            or digest(value['policy']) != digest(POLICY) or type(value['owner']) is not dict
            or set(value['owner']) != OWNER_FIELDS
            or value['binding_digest'] != digest({k: v for k, v in value.items() if k != 'binding_digest'})):
        raise ValueError('Occurrence availability policy binding differs')
    owner = value['owner']
    if str(uuid.UUID(owner['run_id'])) != owner['run_id'] or date.fromisoformat(owner['business_date']).isoformat() != owner['business_date']:
        raise ValueError('Occurrence availability run/date differs')
    for name, width in (('input_digest', 64), ('configuration_digest', 64), ('source_commit', 40)):
        if type(owner[name]) is not str or re.fullmatch('[0-9a-f]{'+str(width)+'}', owner[name]) is None:
            raise ValueError('Occurrence availability identity differs: '+name)
    if owner['predecessor_id'] is None:
        if owner['predecessor_output_digest'] is not None:
            raise ValueError('Occurrence availability initial owner differs')
    elif (str(uuid.UUID(owner['predecessor_id'])) != owner['predecessor_id']
          or type(owner['predecessor_output_digest']) is not str
          or re.fullmatch('[0-9a-f]{64}', owner['predecessor_output_digest']) is None):
        raise ValueError('Occurrence availability predecessor differs')
    if type(owner['execution_revision']) is not str or not 1 <= len(owner['execution_revision']) <= 80:
        raise ValueError('Occurrence availability execution revision differs')
    if (norm is not None or horizon is not None) and (type(norm) is not int or norm not in (0, 1, 2) or horizon != 30):
        raise ValueError('Occurrence availability cannot extend report scope')
    return value


def owner_for(run, configuration_digest, source_commit):
    return dict(run_id=str(run.pk), business_date=run.business_date.isoformat(),
        input_digest=run.input_digest, configuration_digest=configuration_digest,
        predecessor_id=str(run.predecessor_id) if run.predecessor_id else None,
        predecessor_output_digest=run.predecessor.output_digest if run.predecessor_id else None,
        execution_revision=run.execution_revision, source_commit=source_commit)


def verify_owner(value, run, configuration_digest):
    require_binding(value)
    if value['owner'] != owner_for(run, configuration_digest, value['owner']['source_commit']):
        raise ValueError('Occurrence availability foreign run/input/profile/predecessor')
    return value


def groups(tables, value, *, norm, horizon=30):
    """Affected typed rows are relational facts, not a large JSON state payload."""
    require_binding(value, norm=norm, horizon=horizon)
    for ordinal, row in enumerate(tables['Norm0Norm1Norm2Report']):
        if row['Occurances'] is None:
            yield dict(ordinal=ordinal, SKUCode=row['SKUCode'], WhCode=row['WHCode'],
                norm=norm, horizon=horizon, field='Occurances', Count=row['Count'],
                TotalSale=row['TotalSale'], classification=CLASSIFICATION)


def verify_export(tables, value, *, norm, horizon=30):
    require_binding(value, norm=norm, horizon=horizon)
    details, exported = tables['Norm0_1_2ReportDetails'], tables['ReportRows']
    if len(details) != len(exported):
        raise ValueError('Occurrence availability detail/export multiplicity differs')
    for detail, row in zip(details, exported, strict=True):
        if detail['Occurances'] is None and row['values'][8] != '"'+DISPLAY+'"':
            raise ValueError('Occurrence availability visible disclosure missing')


def export_sources(state, value, *, norm, horizon=30):
    """Project availability only into export sources, retaining typed NULL state.

    The ordinary deferred formatter and its retained recipe remain unchanged.
    These are separately owned presentation rows, not replacements for details.
    """
    require_binding(value,norm=norm,horizon=horizon)
    return dict(ui_ReportConfigurations=state['ui_ReportConfigurations'],
        Norm0_1_2ReportDetails=[dict(row,Occurances=DISPLAY) if row['Occurances'] is None
            else row for row in state['Norm0_1_2ReportDetails']])


def summaries(reports, value):
    """Bounded per-family metadata; all affected rows remain in typed images."""
    import hashlib
    from mta.serialization import canonical_parts
    require_binding(value)
    result = {}
    for report in reports:
        norm = STAGES.get(report['stage'])
        if norm is None:
            continue
        hasher = hashlib.sha256()
        count = 0
        keys = set()
        for row in groups(report['tables'], value, norm=norm):
            count += 1
            keys.add((row['SKUCode'], row['WhCode']))
            for part in canonical_parts(row):
                hasher.update(part)
        result[report['stage']] = dict(norm=norm, horizon=30, field='Occurances',
            affected_rows=count, affected_groups=len(keys), affected_rows_digest=hasher.hexdigest(),
            classification=CLASSIFICATION, binding_digest=value['binding_digest'])
    return result
