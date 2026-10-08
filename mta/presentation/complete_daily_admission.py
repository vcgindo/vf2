"""Standalone evidence validators; no publication authorization or parity write.

The controller supplies the pinned contract and independently qualified source
records. Execution claims cannot replace qualification. No existing reader uses
this module; READY issuance awaits the authoritative complete-operation owner.
"""
from datetime import date
from pathlib import PurePosixPath
import re
from uuid import UUID
from mta.serialization import digest

HEX = re.compile(r'[0-9a-f]{64}\Z')
BINDING_FIELDS = ('owner_id', 'database_name', 'run_id', 'business_date',
    'predecessor_id', 'predecessor_output_digest', 'input_digest',
    'input_manifest_digest', 'output_digest', 'production_digest',
    'action_digest', 'source_digest', 'configuration_digest',
    'publication_seal', 'layers_digest', 'activation_digest',
    'permissions_digest', 'hierarchy_digest', 'btr_generation')


def _reject(reason):
    raise ValueError('complete_daily_' + reason)


def _sha(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def _uuid(value):
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except ValueError:
        return False


def validate_binding(actual, expected):
    """Compare with identities independently read from committed native owners.

    Expected must include database ownership, predecessor, ordered action state,
    native source/readback, publication/access seals and selected generation.
    A matched tuple alone is not authority to serve or to issue READY.
    """
    if set(actual) != set(BINDING_FIELDS) or set(expected) != set(BINDING_FIELDS):
        _reject('binding_roster_mismatch')
    if actual != expected:
        _reject('binding_mismatch')
    if any(not _uuid(actual[name]) for name in ('owner_id', 'run_id', 'btr_generation')):
        _reject('invalid_binding_uuid')
    if actual['predecessor_id'] is None:
        if actual['predecessor_output_digest'] != '':
            _reject('initial_predecessor_mismatch')
    elif not _uuid(actual['predecessor_id']) or not _sha(actual['predecessor_output_digest']):
        _reject('invalid_predecessor_binding')
    try:
        if date.fromisoformat(actual['business_date']).isoformat() != actual['business_date']:
            _reject('invalid_business_date')
    except (TypeError, ValueError):
        _reject('invalid_business_date')
    database = actual['database_name']
    if not isinstance(database, str) or not database or database != database.strip():
        _reject('invalid_database_binding')
    for name in BINDING_FIELDS:
        if name.endswith('_digest') or name == 'publication_seal':
            if name == 'predecessor_output_digest' and actual['predecessor_id'] is None:
                continue
            if not _sha(actual[name]):
                _reject('invalid_binding_digest')
    return digest(actual)


def _source(value):
    return (isinstance(value, dict) and set(value) == {'path', 'sha256'}
            and isinstance(value['path'], str) and bool(value['path'])
            and _sha(value['sha256']))


def _relative_path(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and '..' not in path.parts and str(path) == value


def validate_operations(contract_operations, records, qualifications):
    """Full ordered roster; qualified native/modern pins; real output evidence.

    Contract entries: id, canonical_source and implementation_source (each
    path/sha256), qualification_sha256, outputs (ordered id/kind plus native
    schema_sha256 for typed, relative path for file, or reason for absence).
    Independent qualifications: operation_id, both source objects, status PASS,
    receipt_sha256, proof_sha256, output_ids. Execution entries: operation_id,
    both source objects, qualification_sha256, clock_id, started_ns,
    completed_ns, status SUCCEEDED, error None, outputs. Each output has id,
    kind, sha256 and verification_sha256; typed adds schema_sha256/row_count,
    file adds path/size_bytes, absence adds the exact qualified reason.

    Output verification receipts must represent complete typed readback or actual
    file verification, not counts. The controller still verifies their bytes and
    native owners; this function validates metadata correspondence only.
    """
    if not isinstance(contract_operations, list) or not contract_operations:
        _reject('operation_contract_required')
    if (not isinstance(records, list) or not isinstance(qualifications, list)
            or any(not isinstance(row, dict) for row in contract_operations + records + qualifications)):
        _reject('operation_evidence_roster_required')
    ids = [row.get('id') for row in contract_operations]
    if any(not isinstance(name, str) or not name for name in ids) or len(set(ids)) != len(ids):
        _reject('operation_contract_duplicate_or_invalid')
    if [row.get('operation_id') for row in records] != ids:
        _reject('operation_order_or_roster_mismatch')
    proof_ids = [row.get('operation_id') for row in qualifications]
    if any(not isinstance(name, str) for name in proof_ids) or len(set(proof_ids)) != len(proof_ids) or set(proof_ids) != set(ids):
        _reject('qualification_roster_mismatch')
    proofs = {row['operation_id']: row for row in qualifications}
    clock, previous_end = None, None
    for spec, row in zip(contract_operations, records, strict=True):
        proof = proofs[spec['id']]
        for field in ('canonical_source', 'implementation_source'):
            if not _source(spec.get(field)) or row.get(field) != spec[field] or proof.get(field) != spec[field]:
                _reject('operation_source_mismatch')
        if (not _sha(spec.get('qualification_sha256'))
                or row.get('qualification_sha256') != spec['qualification_sha256']
                or proof.get('receipt_sha256') != spec['qualification_sha256']
                or proof.get('status') != 'PASS' or not _sha(proof.get('proof_sha256'))):
            _reject('operation_not_qualified')
        if row.get('status') != 'SUCCEEDED' or 'error' not in row or row['error'] is not None:
            _reject('operation_not_successful')
        start, end = row.get('started_ns'), row.get('completed_ns')
        if (type(start) is not int or type(end) is not int or start < 0 or end < start
                or previous_end is not None and start < previous_end):
            _reject('operation_timing_invalid')
        if not isinstance(row.get('clock_id'), str) or not row['clock_id']:
            _reject('operation_clock_required')
        if clock is not None and row['clock_id'] != clock:
            _reject('operation_clock_mismatch')
        clock, previous_end = row['clock_id'], end
        output_specs, outputs = spec.get('outputs'), row.get('outputs')
        if (not isinstance(output_specs, list) or not isinstance(outputs, list)
                or any(not isinstance(item, dict) for item in output_specs + outputs)):
            _reject('operation_outputs_required')
        output_ids = [item.get('id') for item in output_specs]
        if (any(not isinstance(name, str) or not name for name in output_ids)
                or len(set(output_ids)) != len(output_ids)
                or [item.get('id') for item in outputs] != output_ids
                or proof.get('output_ids') != output_ids):
            _reject('operation_output_roster_mismatch')
        for output_spec, output in zip(output_specs, outputs, strict=True):
            kind = output_spec.get('kind')
            if kind not in ('typed', 'file', 'absence') or output.get('kind') != kind:
                _reject('operation_output_kind_mismatch')
            if not _sha(output.get('sha256')) or not _sha(output.get('verification_sha256')):
                _reject('operation_output_unverified')
            if kind == 'typed':
                if (not _sha(output.get('schema_sha256'))
                        or output['schema_sha256'] != output_spec.get('schema_sha256')
                        or type(output.get('row_count')) is not int or output['row_count'] < 0):
                    _reject('typed_output_invalid')
            elif kind == 'file':
                if (not _relative_path(output.get('path')) or output['path'] != output_spec.get('path')
                        or type(output.get('size_bytes')) is not int or output['size_bytes'] < 0):
                    _reject('file_output_invalid')
            elif not isinstance(output_spec.get('reason'), str) or not output_spec['reason'] or output.get('reason') != output_spec['reason']:
                _reject('absence_output_invalid')
    return digest(dict(operations=records, qualifications=qualifications))
