"""Finite process-restart storage proof, never a business scope command."""
import json
import os
import sys

if os.environ.get('VF_PHASE_POSTGRES_PROOF') != '1':
    raise RuntimeError('Explicit owned phase process proof required')
import django
django.setup()
from django.db import connection, transaction
from mta.application.native_output_contracts import native_assignments
from mta.runtime import phase_state
from mta.runtime.models import CalculationRun, DailyPhaseSnapshot
from mta.runtime.relational_state import production_projection
from mta.serialization import storage
from mta.temporal import chain
from tests.test_phase_state_postgresql import PhaseStatePostgresTests

if connection.settings_dict['NAME'] != 'VFTEST_Fresh_LifecycleG2_20261024':
    raise RuntimeError('Process proof must use its uniquely owned test database')


def comparable(output, sources):
    return storage(dict(projection=production_projection(output),
        sources=sources.__dict__, extras={key: output[key] for key in (
            '_PickSourceDigests', '_MasterPreparation', '_OperationalInputTables',
            '_OperationalForceSources', '_CompletedBoundaries', '_Cohort1')}))


probe = PhaseStatePostgresTests()
action = sys.argv[1]
with native_assignments(True):
    if action == 'start':
        from copy import deepcopy
        with transaction.atomic():
            run, bpr, sources = probe.owner()
            reference = comparable(chain.produce_btr(chain.produce_dbm(deepcopy(bpr))), sources)
            snapshot = phase_state.save(run, bpr, sources)
        result = dict(run_id=str(run.pk), phase='BPR', reference=reference)
    else:
        run = CalculationRun.objects.get(pk=sys.argv[2])
        snapshot = DailyPhaseSnapshot.objects.get(run=run, phase='BPR' if action == 'dbm' else 'DBM')
        phase, sources = phase_state.read(snapshot, **probe.references(run))
        if action == 'dbm':
            dbm = chain.produce_dbm(phase)
            with transaction.atomic():snapshot = phase_state.save(run, dbm, sources, parent=snapshot)
            result = dict(run_id=str(run.pk), phase='DBM', state_digest=snapshot.state_digest)
        elif action == 'btr':
            final = chain.produce_btr_from_snapshot(phase, sources,
                pick_source_digests=snapshot.manifest['metadata']['pick_source_digests'])
            result = dict(run_id=str(run.pk), phase='TERMINAL_PRODUCER',
                          actual=comparable(final.output, final.calculation_sources))
        else:raise ValueError('Unknown finite proof action')
    run.refresh_from_db()
    if run.status != 'RUNNING' or run.output_digest or run.checkpoints.exists():
        raise AssertionError('Calculation storage must not promote the day')
print('PHASE_PROOF='+json.dumps(result, separators=(',', ':')))
