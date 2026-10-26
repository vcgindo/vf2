"""One dedicated PostgreSQL session owns an operational worker's lifetime."""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import uuid
from datetime import datetime

import psycopg
from psycopg import sql
from psycopg.pq import TransactionStatus
from django.conf import settings
from django.db import connection

_current=ContextVar('fresh_operational_lease',default=None)


class OperationalLeaseError(ValueError):
    pass


class OperationalRunLease:
    def __init__(self,run_id,session):
        self.run_id=uuid.UUID(str(run_id))
        self.key=int.from_bytes(hashlib.sha256(('fresh-operational:'+str(self.run_id)).encode()).digest()[:8],
                                'big',signed=True)
        self.owner=uuid.uuid4()
        self.session=session
        self.backend_pid=session.info.backend_pid

    def check(self):
        if self.session.closed:
            raise OperationalLeaseError('Operational worker lease connection is closed')
        try:
            held=self.session.execute('''SELECT EXISTS(SELECT 1 FROM pg_locks
                WHERE locktype='advisory' AND pid=pg_backend_pid() AND granted
                AND database=(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database())
                AND classid=%s AND objid=%s AND objsubid=1)''',
                ((self.key>>32)&0xffffffff,self.key&0xffffffff)).fetchone()[0]
        except psycopg.Error as error:
            raise OperationalLeaseError('Operational worker lease connection was lost') from error
        if not held:raise OperationalLeaseError('Operational worker lease is not held')
        return self

    @contextmanager
    def publication_transaction(self,attempt):
        """Yield the lease cursor for a later, explicitly supported registrar.

        This foundation grants no operational publication capability. The caller
        must still authenticate its complete captured request/source/config and
        obey the publication guard. No ORM read or mutation belongs inside this
        dedicated transaction. A commit acknowledgement error is not evidence
        of rollback; resolve immutable receipts under a newly authorized lease.
        """
        if (_current.get() is not self or self.run_id!=uuid.UUID(str(attempt.run_id))
                or attempt.lease_key!=self.key or attempt.lease_owner!=self.owner):
            raise OperationalLeaseError('Actual matching operational publication lease required')
        if connection.in_atomic_block or not connection.get_autocommit():
            raise OperationalLeaseError('Publication cannot enter while Django owns a transaction')
        if (self.session.closed or not self.session.autocommit
                or self.session.info.transaction_status!=TransactionStatus.IDLE):
            raise OperationalLeaseError('Publication requires the idle dedicated autocommit lease session')
        self.check()
        try:
            with self.session.transaction():
                with self.session.cursor() as cursor:
                    registration=_publication_role(cursor,self)
                    _publication_locks(cursor,self,attempt)
                    yield cursor
                    # Neither a caller's role switch nor lost worker ownership
                    # can survive the final check immediately before COMMIT.
                    _publication_role(cursor,self,expected=registration)
                    _publication_lock(cursor,self)
        except psycopg.Error as error:
            raise OperationalLeaseError('Publication connection/transaction failed; commit outcome '
                'may be unknown, resolve immutable receipt under a fresh authorized lease') from error


def _publication_lock(cursor,lease):
    cursor.execute('''SELECT pg_backend_pid(), EXISTS(SELECT 1 FROM pg_catalog.pg_locks
        WHERE locktype='advisory' AND pid=pg_backend_pid() AND granted
        AND database=(SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database())
        AND classid=%s AND objid=%s AND objsubid=1)''',
        ((lease.key>>32)&0xffffffff,lease.key&0xffffffff))
    pid,held=cursor.fetchone()
    if pid!=lease.backend_pid or held is not True:
        raise OperationalLeaseError('Publication requires this PID and current-database lease lock')


def _publication_role(cursor,lease,*,expected=None):
    from mta.mdm import owned_namespace as owned
    database=owned._database_identity(cursor)
    if database['name']!=connection.settings_dict['NAME']:
        raise OperationalLeaseError('Publication database differs from configured namespace')
    if expected is None:
        if (database['current_user_oid']!=database['session_user_oid']
                or not owned._plain_role(database['owner'],login=False)):
            raise OperationalLeaseError('Publication requires an issuer session and unprivileged NOLOGIN owner')
        # Do not assume NOINHERIT issuer can SELECT the registry before entry.
        # Match authorize_install: enter the actual pg_database owner, then
        # authenticate that owner/session against provisioner-owned registration.
        cursor.execute("SELECT pg_catalog.pg_has_role(%s::oid,%s::oid,'MEMBER')",
                       (database['session_user_oid'],database['owner']['oid']))
        if cursor.fetchone()!=(True,):
            raise OperationalLeaseError('Publication issuer cannot enter the database owner role')
        cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(database['owner']['name'])))
        after=owned._database_identity(cursor)
        if any(after[key]!=database[key] for key in ('oid','name','owner','session_user_oid')):
            raise OperationalLeaseError('Publication database/session changed during role entry')
        database=after
    registration=owned._registered_identity(cursor)
    owned._validate_identity(database,registration,
        owned._catalogue_evidence(cursor,database,registration),installer=True)
    if expected is not None and registration!=expected:
        raise OperationalLeaseError('Publication namespace registration changed')
    _publication_lock(cursor,lease)
    return registration


def _publication_locks(cursor,lease,attempt):
    """Same supplier advisory namespace/order as services.finish_run.

    The source lookup is rechecked after source/run/attempt locking. The action
    cut reproduces operational_attempts._identity's DBM receipt identity, not its
    business-state replay. Full source/readback verification remains its owner.
    """
    from mta.mdm.supplier_revisions import _key
    from mta.domain.elephant_orders import ACTION
    from mta.serialization import digest
    capture_sql='SELECT source_id,status FROM mta.fresh_mta_mdmdailyinputcapture WHERE run_id=%s'
    cursor.execute(capture_sql,(lease.run_id,))
    capture=cursor.fetchone()
    if capture is None or capture[1]!='CONSUMED':
        raise OperationalLeaseError('Publication requires the completed captured MDM source')
    cursor.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(_key(capture[0]),))
    cursor.execute('''SELECT kind,status,business_date,input_digest,output_digest,production_digest
        FROM mta.fresh_mta_calculationrun WHERE id=%s FOR UPDATE''',(lease.run_id,))
    run=cursor.fetchone()
    cursor.execute('''SELECT run_id,status,business_date,run_output_digest,action_digest,
        source_digest,configuration_id,lease_key,lease_owner
        FROM mta.fresh_mta_operationalattempt WHERE id=%s FOR UPDATE''',(attempt.pk,))
    row=cursor.fetchone()
    cursor.execute(capture_sql,(lease.run_id,))
    if cursor.fetchone()!=capture:
        raise OperationalLeaseError('Publication capture changed during locking')
    if (run is None or run[:2]!=('DAILY_CHAIN','SUCCEEDED') or row is None
            or row!=(lease.run_id,'RUNNING',attempt.business_date,attempt.run_output_digest,
                     attempt.action_digest,attempt.source_digest,attempt.configuration_id,
                     lease.key,lease.owner)
            or run[2]!=row[2] or run[4]!=row[3]):
        raise OperationalLeaseError('Publication attempt/run/output/worker identity differs')
    cursor.execute('''SELECT id,payload,digest,before_digest,after_digest,state_sealed
        FROM mta.fresh_mta_runcommand WHERE run_id=%s AND phase_acceptance_id IS NULL ORDER BY id''',
        (lease.run_id,))
    actions=[]
    last_date=run[2]
    for identity,payload,checksum,before,after,sealed in cursor.fetchall():
        if type(payload) is not dict or digest(payload)!=checksum or sealed is not True:
            raise OperationalLeaseError('Publication action payload/seal differs')
        try:
            event_date=datetime.fromisoformat(payload['timestamp']).date()
        except (KeyError,TypeError,ValueError) as error:
            raise OperationalLeaseError('Publication action timestamp differs') from error
        if event_date<last_date:
            raise OperationalLeaseError('Publication action order differs')
        last_date=event_date
        if payload.get('operation')!=ACTION:
            actions.append(dict(id=identity,digest=checksum,before=before,after=after))
    if (digest(actions)!=row[4] or digest(dict(input=run[3],output=run[4],
            production=run[5],actions=actions))!=row[5]):
        raise OperationalLeaseError('Publication action/source identity differs')
    _publication_lock(cursor,lease)


@contextmanager
def operational_run_lease(run_id):
    if _current.get() is not None:
        raise OperationalLeaseError('Nested operational worker lease is forbidden')
    db=connection.settings_dict
    with psycopg.connect(dbname=db['NAME'],host=db['HOST'],port=db['PORT'] or '5432',
                         user=db['USER'],password=db['PASSWORD'],autocommit=True) as session:
        lease=OperationalRunLease(run_id,session)
        if not session.execute('SELECT pg_try_advisory_lock(%s)',(lease.key,)).fetchone()[0]:
            raise OperationalLeaseError('A live worker owns this operational run')
        token=_current.set(lease)
        try:
            yield lease.check()
        finally:
            _current.reset(token)
            # Closing the dedicated session releases the lock even if the
            # connection has failed; never hide the worker's original error.
            session.close()


def require_run_lease(run_id):
    lease=_current.get()
    if lease is None:
        if getattr(settings,'VF_OPERATIONAL_UNLEASED_TESTS',False):return None
        raise OperationalLeaseError('Live operational worker lease required')
    if lease.run_id!=uuid.UUID(str(run_id)):
        raise OperationalLeaseError('Operational worker lease belongs to another run')
    return lease.check()


def require_attempt_lease(attempt):
    lease=require_run_lease(attempt.run_id)
    if lease is None:
        if attempt.lease_key is None and attempt.lease_owner is None:return None
        raise OperationalLeaseError('Managed attempt cannot use an unleased test worker')
    if attempt.lease_key!=lease.key or attempt.lease_owner!=lease.owner:
        raise OperationalLeaseError('Attempt belongs to another operational worker')
    return lease
