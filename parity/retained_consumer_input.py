"""Read bounded selected tables from a retained, rollback-based oracle capture."""
import gzip
import json
from pathlib import Path

import ijson
from ijson.common import ObjectBuilder

from mta.serialization import digest
from parity.output_archive import file_sha
from parity.temporal import fingerprint

RECEIPT_SHA = '9f502ea08bc580db1149e3e38371ea62a0d01e61e56245ead027b43ece918c60'
RECEIPT = Path('D:/freshvcf-build/evidence/f2-runtime-memory-sql-full-011/replay.json')
STATE_FIELDS = ('BPR_Table','BPRDailyConsumption','LastBatchRunTbl','vf_RationedReqReport')


def selected_capture_tables(path,*,include_routes=False,include_requirements=False,include_master=False):
    """Never build irrelevant intermediate stages or the whole daily trace."""
    selected, late, stage = {}, {}, None
    builder, depth, target = None, 0, None
    with gzip.open(path,'rb') as stream:
        for prefix, event, value in ijson.parse(stream, use_float=True):
            if builder is not None:
                builder.event(event,value)
                depth += int(event in ('start_map','start_array')) - int(event in ('end_map','end_array'))
                if depth == 0:
                    if target.startswith('late/'):
                        late[target[5:]] = builder.value
                    else:
                        selected[target] = builder.value
                    builder = None
                continue
            if prefix == 'output.BPRStages.item.stage' and event == 'string':
                stage = value
            target = None
            if prefix == 'closing':
                target = 'closing'
            elif prefix == 'output.CalculationCheckpoints.bifurcation':
                target = 'bands'
            elif include_routes and prefix == 'output.CalculationCheckpoints.routes':
                target = 'routes'
            elif include_requirements and prefix == 'native_inputs.vf_ReqCalculation':
                target = 'requirements'
            elif include_master and prefix == 'native_inputs.BPRMaster':
                target = 'bpr_master'
            elif stage == 'UpdateBPR.sql':
                for field in STATE_FIELDS:
                    if prefix == 'output.BPRStages.item.state.'+field:
                        target = 'late/'+field
            if target is not None and event in ('start_map','start_array'):
                if target in selected or (target.startswith('late/') and target[5:] in late):
                    raise ValueError('Retained consumer table occurs more than once')
                builder, depth = ObjectBuilder(), 1
                builder.event(event,value)
    required={'closing','bands'} | ({'routes'} if include_routes else set()) | ({'requirements'} if include_requirements else set()) | ({'bpr_master'} if include_master else set())
    if builder is not None or set(late) != set(STATE_FIELDS) or set(selected) != required:
        raise ValueError('Retained consumer source roster incomplete')
    selected['late'] = late
    return selected


def terminal_inputs(*,include_routes=False,include_requirements=False,include_master=False):
    if file_sha(RECEIPT) != RECEIPT_SHA:
        raise ValueError('Accepted legacy receipt changed')
    receipt = json.loads(RECEIPT.read_text())
    entry = receipt['days'][-1]
    if entry['day_index'] != 11 or entry['date'] != '2026-06-17' or entry['status'] != 'PASS_WITH_LEGACY_FLAWS':
        raise ValueError('Terminal receipt identity differs')
    path = Path(entry['legacy_capture_path'])
    before = file_sha(path)
    if (include_routes or include_requirements or include_master) and before!='7e62d8e6d1415537fa780c4b19915d84d205fbf20d3620c953a0a581bf50a730':
        raise ValueError('Pinned accepted terminal route capture differs')
    values = selected_capture_tables(path,include_routes=include_routes,include_requirements=include_requirements,include_master=include_master)
    if file_sha(path) != before:
        raise ValueError('Legacy capture changed during streaming read')
    if digest(values['closing']) != entry['closing_digest']:
        raise ValueError('Retained closing differs from accepted receipt')
    late = dict(values['late'])
    late['BPRLastBatchRunTbl'] = late.pop('LastBatchRunTbl')
    if fingerprint(late) != entry['legacy_boundaries']['final-bpr-bluezone']:
        raise ValueError('Retained BPR boundary differs from accepted receipt')
    if include_routes:
        comparison=[r for r in entry['comparisons'] if r['contract']=='calculation/routes']
        if len(comparison)!=1 or comparison[0]['status']!='PASS' or comparison[0]['legacy_rows']!=len(values['routes']):
            raise ValueError('Original-route capture lacks accepted comparison')
    return values, dict(receipt=str(RECEIPT),receipt_sha256=RECEIPT_SHA,
        capture=str(path),capture_sha256=before,closing_digest=entry['closing_digest'],
        bpr_boundary_fingerprint=entry['legacy_boundaries']['final-bpr-bluezone'],
        date=entry['date'],modern_run=entry['modern_run'],modern_output_digest=entry['modern_output_digest'])
