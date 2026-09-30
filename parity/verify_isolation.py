"""Bounded SQL ownership verification; no live-database writes or data reads."""
import json
from pathlib import Path
import threading
from parity.legacy_isolation import exclusive_replay, connection, MAPPING, PRINCIPAL
from parity.provision_legacy import schema_signature


def verify(destination):
    destination=Path(destination)
    if destination.exists():raise ValueError('Evidence already exists')
    with exclusive_replay(),connection('VFTEST_Importer') as conn:
        row=conn.execute("SELECT SUSER_SNAME(),IS_SRVROLEMEMBER('sysadmin'),HAS_PERMS_BY_NAME(NULL,NULL,'CONTROL SERVER')").fetchone()
        if tuple(row)!=(PRINCIPAL,0,0):raise ValueError('Execution privilege escape')
        forbidden=[]
        # Metadata only. A context switch/access to another user database must
        # be impossible, even if a future trusted adapter bypasses token checks.
        for name,accessible in conn.execute("SELECT name,HAS_DBACCESS(name) FROM sys.databases WHERE database_id>4"):
            if name not in MAPPING.values() and accessible:forbidden.append(name)
        if forbidden:raise ValueError('Principal can access unrelated databases: '+str(forbidden))
        errors=[]
        def outsider():
            try:connection('VFTEST_BPR')
            except ValueError as error:errors.append(str(error))
        thread=threading.Thread(target=outsider);thread.start();thread.join()
        if len(errors)!=1 or 'lease' not in errors[0]:raise ValueError('Cross-thread ownership escaped')
        before=schema_signature(conn)
        conn.execute('BEGIN TRANSACTION')
        try:
            conn.execute('CREATE TABLE dbo.FreshSchemaIntegrityProbe (id int NOT NULL)')
            if schema_signature(conn)==before:raise ValueError('Schema drift was invisible')
        finally:conn.execute('ROLLBACK TRANSACTION')
        if schema_signature(conn)!=before:raise ValueError('Schema probe did not restore exact state')
    result=dict(status='PASS',principal=PRINCIPAL,server_admin=False,unrelated_database_access=False,
                cross_thread_denied=True,schema_drift_detected=True,probe_schema_restored=True)
    destination.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':
    import sys
    verify(sys.argv[1])
