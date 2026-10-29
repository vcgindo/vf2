"""Private owner-only transaction context after joint daily input admission.

Call after setting the ordinary current/consuming/phase markers and creating
the pending closing receipt (Full). The existing transaction retains every
write, effect, epoch and acceptance producer. This optimization trusts the
database function owner, which can already replace these trigger functions;
restricted SQL roles cannot enable it by setting custom GUCs.
"""
from contextlib import contextmanager
from django.db import connection, DatabaseError, transaction
from mta.application import accepted_inputs

GUARDS = ('guard_active_mdm_current', 'guard_prepared_effect',
          'guard_scoped_current_copy', 'guard_location_projection_statement')
SETTINGS = ('fresh.accepted_current_xid', 'fresh.accepted_current_run')


@contextmanager
def _accepted_current_write(run, source):
    try:
        with _current_writer_context(run, source):
            yield
    except DatabaseError:
        # A raw setup SELECT/SET may abort PostgreSQL before __enter__ returns.
        # Mark that rollback too, before the enclosing publisher cleans up.
        transaction.set_rollback(True)
        raise


@contextmanager
def _current_writer_context(run, source):
    admitted = accepted_inputs._current.get()
    if (type(admitted) is not accepted_inputs._AcceptedInputs
            or admitted.owner != str(run.pk)):
        raise ValueError('Current write context requires its joint daily intake owner')
    if connection.vendor != 'postgresql' or not connection.in_atomic_block:
        raise ValueError('Accepted current writes require their PostgreSQL transaction')
    with connection.cursor() as cursor:
        cursor.execute('SELECT count(*)=4 AND bool_and('
            'pg_catalog.pg_get_userbyid(P.proowner)=CURRENT_USER) '
            'FROM pg_catalog.pg_proc P JOIN pg_catalog.pg_namespace N ON N.oid=P.pronamespace '
            "WHERE N.nspname='mta' AND P.proname=ANY(%s) AND P.pronargs=0", [list(GUARDS)])
        if cursor.fetchone() != (True,):
            raise ValueError('Accepted current writes require the existing guard owner role')
        cursor.execute("SELECT R.kind,R.status,C.status,C.source_id,S.receipt->>'schema',"
            "nullif(current_setting('fresh.mdm_current_run',true),''),"
            "nullif(current_setting('fresh.mdm_consuming_run',true),''),"
            'mta.pending_scoped_current(S.id),'
            'EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt A WHERE A.run_id=R.id) '
            'FROM mta.fresh_mta_calculationrun R '
            'JOIN mta.fresh_mta_mdmdailyinputcapture C ON C.run_id=R.id '
            'JOIN mta.fresh_mta_mdmsource S ON S.id=C.source_id '
            'WHERE R.id=%s AND S.id=%s FOR UPDATE OF R,C,S', [run.pk, source.pk])
        state = cursor.fetchone()
        if (state is None or state[:2] != ('DAILY_CHAIN', 'RUNNING')
                or state[3] != source.pk or state[4] != 'fresh-production-mdm-source-v1'
                or state[5] != str(run.pk)):
            raise ValueError('Accepted current command source or run differs')
        capture, consuming, phase, scoped = state[2], state[6], state[7], state[8]
        if scoped:
            valid = ((phase == 'PRE_BPR' and capture == 'CAPTURED' and consuming == str(run.pk))
                or (phase in ('BPR', 'DBM') and capture == 'CAPTURED' and consuming is None)
                or (phase == 'DAY_FINAL' and capture == 'CONSUMED' and consuming is None))
            if not valid:
                raise ValueError('Accepted current scoped command is not its pending producing phase')
        else:
            if phase is not None or capture != 'CONSUMED' or consuming != str(run.pk):
                raise ValueError('Accepted current Full command requires its consumed day')
            cursor.execute('SELECT P.status,mta.valid_closing_projection(P) '
                'FROM mta.fresh_mta_mdmclosingprojectionreceipt P WHERE P.run_id=%s '
                'FOR UPDATE OF P', [run.pk])
            if cursor.fetchone() != ('PENDING', True):
                raise ValueError('Accepted current Full command requires its pending closing receipt')
        cursor.execute('SELECT pg_catalog.txid_current()::text,'
            "current_setting('fresh.accepted_current_xid',true),"
            "current_setting('fresh.accepted_current_run',true)")
        xid, previous_xid, previous_run = cursor.fetchone()
        cursor.execute('SELECT set_config(%s,%s,true),set_config(%s,%s,true)',
            [SETTINGS[0], xid, SETTINGS[1], str(run.pk)])
    try:
        yield
    except DatabaseError:
        transaction.set_rollback(True)
        raise
    finally:
        if connection.in_atomic_block and not connection.needs_rollback and not connection.closed_in_transaction:
            with connection.cursor() as cursor:
                cursor.execute('SELECT set_config(%s,%s,true),set_config(%s,%s,true)',
                    [SETTINGS[0], previous_xid or '', SETTINGS[1], previous_run or ''])
