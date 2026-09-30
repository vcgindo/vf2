"""Separate validation traces from the production state/read models."""
import json
import os
from pathlib import Path

from parity.output_archive import OutputArchive, write_rows
from parity.output_archive import iter_rows
from mta.temporal.chain import DELIVERY_TABLES
from mta.serialization import digest

TRACE_NAMES = frozenset(('MasterValidation', 'SupplierStages', 'DailyStages',
    'ControlStages', 'OrderStages', 'BPRStages', 'DBMStages', 'BTRStages', 'MajorBoundaries'))


def evidence_path(run, name):
    root = os.environ.get('VF_EVIDENCE_ROOT')
    if not root:
        raise ValueError('VF_EVIDENCE_ROOT is required for validation traces')
    if name not in DELIVERY_TABLES and name!='InputSnapshot':
        raise ValueError('Only declared validation traces belong outside production storage')
    base = Path(root).resolve()
    path = (base / str(run.pk) / (name + '.jsonl.gz')).resolve()
    if path.parent.parent != base:
        raise ValueError('Validation evidence path escaped its owner')
    return path


def store_input(run_id,raw):
    from types import SimpleNamespace
    owner=SimpleNamespace(pk=run_id)
    path=evidence_path(owner,'InputSnapshot')
    metadata=write_rows(path,[raw])
    return dict(schema='fresh-input-reference-v1',path=str(run_id)+'/InputSnapshot.jsonl.gz',
        **metadata,profile={'delivery':{'site_code':raw['profile']['delivery']['site_code']}},
        input_digest=digest(raw))


def read_input(run):
    value=run.input_payload
    if value.get('schema')!='fresh-input-reference-v1':return value
    if value['path']!=str(run.pk)+'/InputSnapshot.jsonl.gz':raise ValueError('Input owner/path drift')
    rows=list(iter_rows(evidence_path(run,'InputSnapshot'),value))
    if len(rows)!=1 or digest(rows[0])!=value['input_digest']:raise ValueError('Input snapshot drift')
    expected={'delivery':{'site_code':rows[0]['profile']['delivery']['site_code']}}
    if value['profile']!=expected:raise ValueError('Input identity metadata drift')
    return rows[0]


def persist_trace(run, name, rows):
    path = evidence_path(run, name)
    metadata = write_rows(path, rows)
    return dict(rows=[], row_count=metadata['row_count'], digest=metadata['digest'],
        evidence_path=str(run.pk) + '/' + name + '.jsonl.gz',
        evidence_sha256=metadata['sha256'])


def export_run(run, directory):
    """Export persisted production rows plus referenced traces; verify all bytes.

    No whole daily output graph is reconstructed. Existing JSON-only runs can
    also be exported without rewriting their stored rows or original receipts.
    """
    from mta.runtime.services import read_outputs
    read_outputs(run)  # Production identity/roster/readback checks first.
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    records = []
    for checkpoint in run.checkpoints.order_by('name').iterator(chunk_size=1):
        if checkpoint.evidence_path:
            path = evidence_path(run, checkpoint.name)
            if checkpoint.evidence_path != str(run.pk) + '/' + checkpoint.name + '.jsonl.gz':
                raise ValueError('Validation evidence owner/path drift')
            metadata = dict(row_count=checkpoint.row_count, digest=checkpoint.digest,
                            sha256=checkpoint.evidence_sha256)
        else:
            path = directory / (checkpoint.name + '.jsonl.gz')
            metadata = write_rows(path, checkpoint.rows)
            if metadata['digest'] != checkpoint.digest or metadata['row_count'] != checkpoint.row_count:
                raise ValueError('Production export checksum differs')
        records.append(dict(name=checkpoint.name, path=os.path.relpath(path, directory), **metadata))
    manifest = directory / 'manifest.json'
    manifest.write_text(json.dumps(dict(schema='fresh-output-archive-v1', run_id=str(run.pk),
        output_digest=run.output_digest, checkpoints=records), indent=2), encoding='utf-8')
    OutputArchive(manifest).verify(run.output_digest)
    return manifest
