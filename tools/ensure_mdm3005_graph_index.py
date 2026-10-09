"""Build the exact target-fixture Seasonality access path; never change rows."""
from pathlib import Path
import subprocess
import sys


SCRIPT = r'''
import os,json,time,gzip,base64
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django;django.setup()
from django.db import connection
from mta.mdm.source import source as selected_source
from mta.mdm.target_fixture import require,daily_pair_rows,RUN,SOURCE
from mta.serialization import digest,canonical_parts
repair=os.environ.get('FRESH_MDM3005_REBUILD_OWNED_INVALID')=='1'
assert connection.settings_dict['HOST']=='freshvcf-test-postgres-1'
assert connection.settings_dict['NAME']=='test_freshvcf_stage2_vm_20261003_002'
assert connection.get_autocommit() and not connection.in_atomic_block
source=selected_source();owner=require(source)
assert source.digest==SOURCE and str(owner.run_id)==RUN
run=owner.run
name='fresh_mdm3005_dailyconsumption_graph'
definition=('CREATE INDEX '+name+' ON mta_state.dbm_dailyconsumption USING btree '
 '(vf_run_id, vf_image, lower(rtrim("SKUCode")), lower(rtrim("WhCode")), '
 '"ReportDate" DESC NULLS LAST, vf_ordinal)')
with connection.cursor() as c:
 c.execute("SELECT indisvalid,indisready,pg_get_indexdef(indexrelid) FROM pg_index WHERE indexrelid=to_regclass(%s)",['mta_state.'+name])
 existing=c.fetchone()
 if existing is not None:
  expected=(False,True,definition) if repair else (True,True,definition)
  assert existing==expected,'Unexpected index; inspect, never silently reuse/drop'
 if repair:
  assert existing is not None,'Recovery requires the exact failed owned index'
  c.execute("SELECT tgenabled,pg_get_triggerdef(oid) FROM pg_trigger WHERE tgrelid='mta_state.dbm_dailyconsumption'::regclass AND tgname='stage2_immutable'")
  assert c.fetchone()==('O','CREATE TRIGGER stage2_immutable BEFORE INSERT OR DELETE OR UPDATE OR TRUNCATE ON mta_state.dbm_dailyconsumption FOR EACH STATEMENT EXECUTE FUNCTION stage2_owner.deny_fixture_mutation()')
captured=[]
def capture(execute,sql,params,many,context):
 if sql.startswith('SELECT "ReportDate","Stock","GIT" FROM ('):
  captured.append((sql,params))
 return execute(sql,params,many,context)
start=time.monotonic()
with connection.execute_wrapper(capture):
 before=daily_pair_rows(source,run,'23102151009146','P024_1001')
assert len(captured)==1
print(json.dumps({'stage':'BEFORE','rows':len(before),'digest':digest(before),'seconds':time.monotonic()-start}),flush=True)
print(json.dumps({'stage':'COMPLETE_BEFORE_ROWS','gzip_base64':base64.b64encode(gzip.compress(b''.join(canonical_parts(before)),mtime=0)).decode()}),flush=True)
if existing is None:
 with connection.cursor() as c:
  c.execute("SET lock_timeout='5s'")
  c.execute("SET statement_timeout='20min'")
  c.execute(definition.replace('CREATE INDEX ','CREATE INDEX CONCURRENTLY ',1))
 print('EXACT_CONCURRENT_INDEX_CREATED',flush=True)
elif repair:
 with connection.cursor() as c:
  c.execute("SET lock_timeout='5s'")
  c.execute("SET statement_timeout='45min'")
  c.execute('REINDEX INDEX CONCURRENTLY mta_state.fresh_mdm3005_dailyconsumption_graph')
 print('EXACT_OWNED_INVALID_INDEX_REBUILT',flush=True)
with connection.cursor() as c:
 c.execute("SELECT indisvalid,indisready,pg_get_indexdef(indexrelid) FROM pg_index WHERE indexrelid=to_regclass(%s)",['mta_state.'+name])
 assert c.fetchone()==(True,True,definition),'Index identity/readiness differs'
start=time.monotonic()
after=daily_pair_rows(source,run,'23102151009146','P024_1001')
assert after==before,'Graph rows/order changed'
with connection.cursor() as c:
 c.execute('EXPLAIN (FORMAT JSON) '+captured[0][0],captured[0][1]);plan=c.fetchone()[0]
assert name in json.dumps(plan),'Graph did not select the new access path'
print(json.dumps({'stage':'AFTER','rows':len(after),'digest':digest(after),'seconds':time.monotonic()-start,'plan':plan,'row_mutations':0}),flush=True)
'''


def main():
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != '--rebuild-owned-invalid'):
        raise SystemExit('Usage: python tools/ensure_mdm3005_graph_index.py OUTPUT_LOG [--rebuild-owned-invalid]')
    path = Path(sys.argv[1])
    image = subprocess.check_output(
        ['docker', 'inspect', '--format', '{{.Image}}', 'freshvcf-preview-mta-1'],
        text=True).strip()
    assert image == 'sha256:b3bc7ea3994db6967a590fb3d5d7b265d680d7bce205f9395643e7efd3582016'
    with path.open('xb') as log:
        command = ['docker', 'exec', '-i']
        if len(sys.argv) == 3:
            command += ['-e', 'FRESH_MDM3005_REBUILD_OWNED_INVALID=1']
        result = subprocess.run(
            command + ['freshvcf-preview-mta-1', 'python', '-'],
            input=SCRIPT.encode(), stdout=log, stderr=subprocess.STDOUT)
    result.check_returncode()
    print('Exact target graph index and row equivalence verified:', path)


if __name__ == '__main__':
    main()
