"""One dedicated PostgreSQL session owns an operational worker's lifetime."""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import uuid

import psycopg
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

    def check(self):
        if self.session.closed:
            raise OperationalLeaseError('Operational worker lease connection is closed')
        try:
            held=self.session.execute('''SELECT EXISTS(SELECT 1 FROM pg_locks
                WHERE locktype='advisory' AND pid=pg_backend_pid() AND granted
                AND classid=%s AND objid=%s AND objsubid=1)''',
                ((self.key>>32)&0xffffffff,self.key&0xffffffff)).fetchone()[0]
        except psycopg.Error as error:
            raise OperationalLeaseError('Operational worker lease connection was lost') from error
        if not held:raise OperationalLeaseError('Operational worker lease is not held')
        return self


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
