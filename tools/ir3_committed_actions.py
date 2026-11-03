"""One approved IR3 positive pair, using normal commits and durable evidence.

Run only on an explicitly approved, pinned, unconsumed fixture. This observer
does not provision data, rewrite scripts, reset state, or retry an action.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

from action_measurement import ActionMeasurement


def file_hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def prior_rows(connection):
    result = {}
    with connection.cursor() as cursor:
        cursor.execute("SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n "
            "ON n.oid=c.relnamespace WHERE c.relkind='r' AND n.nspname NOT IN "
            "('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%%' "
            "AND has_table_privilege(c.oid,'SELECT') ORDER BY 1,2")
        for schema, table in cursor.fetchall():
            if (schema, table) == ('mta', 'fresh_mta_ingestionrevisionstate'):
                continue
            qualified = connection.ops.quote_name(schema)+'.'+connection.ops.quote_name(table)
            cursor.execute('SELECT row_to_json(t)::text FROM '+qualified+' t')
            counts = Counter()
            while records := cursor.fetchmany(500):
                counts.update(hashlib.sha256(row[0].encode()).hexdigest() for row in records)
            result[schema+'.'+table] = counts
    return result


def main(spec_path, preflight_only=False):
    spec = json.loads(Path(spec_path).read_bytes())
    workroot, inputroot = Path(spec['work_root']), Path(spec['input_root'])
    proof = json.loads(Path(spec['fixture_proof']).read_bytes())
    expected = json.loads(Path(spec['expected_actions']).read_bytes())
    journal = json.loads((workroot/'csv-scopes/2026-10-24/operation.json').read_bytes())
    if journal['status'] != 'PUBLISHED' or journal['scope'] != 'UptoBPR':
        raise ValueError('Fixture has no published positive action boundary')
    os.environ.update(journal['environment'])
    permissions = inputroot/'permissions.json'
    os.environ.update(VF_MTA_PERMISSIONS_FILE=str(permissions),
        VF_MTA_PERMISSIONS_SHA256=hashlib.sha256(permissions.read_bytes()).hexdigest())
    from release.daily_serving_check import configure_image
    configure_image()
    import django
    django.setup()
    from django.db import connection
    from mta.runtime.models import CalculationRun, RunPhaseAcceptance
    from mta.runtime.ingestion_models import IngestionRevisionState
    from mta.runtime.accepted_state_read import read_accepted_daily
    from mta.runtime import scoped_actions
    from mta.presentation import (scoped_action_writer, scoped_selection, actions,
                                  scoped_report_storage, scoped_prepared, scoped_planning)
    from mta.serialization import digest, storage

    # Existing qualified candidate installer pins all source bytes. It does not
    # alter the image, persistent application files, or any historical recipe.
    os.environ.update(IR3_CANDIDATE_ROOT=spec['candidate_root'],
                      IR3_CANDIDATE_MANIFEST=spec['candidate_manifest'])
    from ir3_actioncost_patch import install
    source = install()
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database(),current_user,session_user')
        if cursor.fetchone() != (spec['database'], 'vectorflow_mta_runtime', 'vectorflow_mta_runtime'):
            raise ValueError('Fixture database or runtime role differs')
    if connection.in_atomic_block:
        raise ValueError('The observer must not wrap normal submit in a transaction')
    run = CalculationRun.objects.get(pk=proof['run'], status='RUNNING')
    phase = RunPhaseAcceptance.objects.select_related('snapshot').get(pk=proof['phase'])
    if (run.commands.exists() or scoped_actions.revision(run) != 0
            or phase.digest != proof['phase_digest']
            or phase.snapshot.state_digest != proof['snapshot_digest']):
        raise ValueError('Fixture is consumed or phase identity differs; do not replay')

    def prefix():
        return {str(v.pk): dict(output=v.output_digest, production=v.production_digest,
                    closing=digest(read_accepted_daily(v, include_reports=False)['ClosingState']))
                for v in CalculationRun.objects.filter(status='SUCCEEDED')}

    def publication(view):
        if view.run_id != run.pk or view.bpr.sources.acceptance_id != phase.pk:
            raise ValueError('Publication belongs to another run or phase')
        return dict(reports=storage({n:view.bpr.reports.rows(n) for n in scoped_report_storage.TABLES}),
            prepared=storage({n:view.bpr.rows(n) for n in scoped_prepared.TABLES}),
            planning=storage({n:view.planning.rows(n) for n in scoped_planning.TABLES}),
            git=storage(view.git.rows()))

    selected = scoped_selection.selected()
    assert selected.action_revision == 0
    publication(selected)  # Explicit warm-up, outside action measurements.
    assert prefix() == proof['old_six_closings']
    actual, _ = scoped_actions.restore(run, phase)
    assert storage(scoped_actions.state_for(actual)) == expected['baseline']
    if preflight_only:
        print(json.dumps(dict(status='PINNED_UNCONSUMED_FIXTURE_PREFLIGHT_PASS', run=str(run.pk))))
        return

    output = Path(spec['output_directory'])
    # Reserve both action journals BEFORE either action can run. A stale file
    # or unsupported identity aborts without consuming the fixture.
    identity = dict(database=spec['database'], run=run.pk, phase=phase.pk, source=source)
    with ActionMeasurement(output/'APPLY.jsonl', identity) as apply_record:
        with ActionMeasurement(output/'SLEEP.jsonl', identity) as sleep_record:
            before_files, before_rows = file_hashes(workroot), prior_rows(connection)
            before_epochs = {str(v['initialization_id']): v for v in IngestionRevisionState.objects.values()}
            baseline = json.loads(Path(spec['matched_baseline']).read_bytes())
            for index, (operation, record) in enumerate((('APPLY', apply_record), ('SLEEP', sleep_record))):
                with patch.object(actions, 'timestamp', return_value='2026-10-24T10:00:00+05:30'):
                    event, response = record.submit(connection,
                        lambda: scoped_action_writer.submit(expected['permission_payload'], 'ir3-owned-proof', operation))
                record.record('command_committed', command_id=event.pk,
                              before_digest=event.before_digest, after_digest=event.after_digest)
                actual, _ = scoped_actions.restore(run, phase)
                state = scoped_actions.state_after(run, phase, actual, expected_revision=event.pk)
                wanted = expected['expected_after_'+operation.lower()]
                assert storage(state) == wanted and event.after_digest == digest(wanted)
                current = scoped_selection.selected()
                assert current.action_revision == event.pk
                assert publication(current) == baseline['events'][index]['rows']
                assert response == baseline['events'][index]['response']
                record.record('independent_action_audit_passed')
            assert run.commands.count() == 2 and prefix() == proof['old_six_closings']
            assert file_hashes(workroot) == before_files
            after_rows = prior_rows(connection)
            assert set(after_rows) == set(before_rows)
            for table, rows in before_rows.items():
                assert not (rows-after_rows[table]), 'Prior row changed: '+table
            after_epochs = {str(v['initialization_id']): v for v in IngestionRevisionState.objects.values()}
            assert set(after_epochs) == set(before_epochs)
            changes = {}
            for key, old in before_epochs.items():
                new = after_epochs[key]
                changes[key] = {k: [old[k], new[k]] for k in old if old[k] != new[k]}
                assert set(changes[key]) <= {'operational_epoch', 'action_epoch'}
                assert all(new[k] >= old[k] for k in changes[key])
            sleep_record.record('complete_preservation_audit_passed', epoch_changes=changes,
                                prior_table_count=len(before_rows))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    main(args.spec, args.preflight_only)
