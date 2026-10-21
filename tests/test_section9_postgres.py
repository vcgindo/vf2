"""Real Pick threshold persistence, read-only readers and fresh-process bytes.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from mta.serialization import digest,storage
from mta.row_sequences import RecordRows
from mta.application.complete_daily_batch_files import reports_from_pick_state,sqlcmd_bytes,write_run_pick_files
from mta.domain.remaining_capabilities import calculate_pick_list_state
from tests.test_pick_stage_state import fixture

NAMES=('LogisticPickList','PickListDataForTruckFormation')


def expected_state(counts):
    base=storage(calculate_pick_list_state(fixture()))
    return {name:[dict(base[name][i%len(base[name])],SKUCode='S'+str(i%11))
        for i in range(size)] for name,size in zip(NAMES,counts)}


def fresh_verify(pk,counts,pins):
    from django.db import connection,transaction
    from mta.runtime.models import CalculationRun
    from mta.presentation.selective import image_rows
    expected=expected_state(counts)
    with patch.dict(os.environ),transaction.atomic():
        os.environ.pop('VF_WORK_ROOT',None)
        with connection.cursor() as cursor:cursor.execute('SET TRANSACTION READ ONLY')
        run=CalculationRun.objects.get(pk=pk)
        state={name:image_rows(run,'closing/complete/'+name) for name in NAMES}
        for name,size in zip(NAMES,counts):
            assert isinstance(state[name],RecordRows)==(size>10000)
            assert list(state[name])==expected[name]
        actual={key:hashlib.sha256(sqlcmd_bytes(value['resultsets'])).hexdigest()
            for key,value in reports_from_pick_state(state).items()}
        assert actual==pins
    print('SECTION9_FRESH_READONLY_PASS '+json.dumps(dict(run=pk,counts=counts,files=actual)))


@unittest.skipUnless(os.environ.get('VF_SECTION9_POSTGRES_PROOF')=='1','Owned small Section9 PostgreSQL proof required')
class Section9PostgresTests(unittest.TestCase):
    def test_pick_both_tables_independent_thresholds_and_mixed_fresh_readers(self):
        from django.db import connection,transaction
        from mta.runtime.models import CalculationRun
        from mta.runtime import relational_state as typed
        from mta.presentation.selective import image_rows
        from mta.presentation import pick_downloads
        self.assertEqual(connection.settings_dict['NAME'],'vf_section9_contracts_20261021')
        counts_cases=[(n,2) for n in (9999,10000,10001)]+[(2,n) for n in (9999,10000,10001)]+[(10001,10001)]
        for counts in counts_cases:
            source=expected_state(counts);before=digest(source)
            expected={key:sqlcmd_bytes(value['resultsets']) for key,value in reports_from_pick_state(source).items()}
            run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2037-04-10',
                execution_revision='section9-pick-'+str(counts),input_digest='9'*64,input_payload={},status='RUNNING')
            images={}
            with transaction.atomic():
                for name in NAMES:
                    path='closing/complete/'+name
                    images[path]=typed.save_image(run,path,path,source[name],table='complete/BPR/'+name)
                run.production_manifest={'images':images};run.status='SUCCEEDED'
                run.save(update_fields=['production_manifest','status'])
            loaded={name:image_rows(run,'closing/complete/'+name) for name in NAMES}
            for name,size in zip(NAMES,counts):
                self.assertEqual(isinstance(loaded[name],RecordRows),size>10000)
                if size>10000:self.assertTrue(hasattr(loaded[name],'_data'),'actual worker file-spool required')
                self.assertEqual(list(loaded[name]),source[name])
            self.assertEqual({key:sqlcmd_bytes(value['resultsets']) for key,value in reports_from_pick_state(loaded).items()},expected)
            self.assertEqual(digest(source),before)
            pins={key:hashlib.sha256(value).hexdigest() for key,value in expected.items()}
            command=[sys.executable,'-c',
                'import os,django;django.setup();from tests.test_section9_postgres import fresh_verify;'
                'import json,sys;fresh_verify(sys.argv[1],json.loads(sys.argv[2]),json.loads(sys.argv[3]))',
                str(run.pk),json.dumps(counts),json.dumps(pins)]
            child=subprocess.run(command,cwd='/proof-code',capture_output=True,text=True,timeout=90)
            self.assertEqual(child.returncode,0,child.stdout+child.stderr)
            print(child.stdout.strip())
            with tempfile.TemporaryDirectory() as td:
                write_run_pick_files(run.pk,loaded,td)
                # Permission resolution is isolated; actual stored rows, file
                # ownership, source regeneration and byte checks are real.
                with patch.object(pick_downloads,'_attributes',return_value={}), \
                        patch.object(pick_downloads,'scope',return_value=({'S'+str(i) for i in range(11)},{'P','L1','L2'})), \
                        patch.object(pick_downloads,'read_input',return_value={'pick_output_root':td}):
                    for report,filename in pick_downloads.REPORTS.items():
                        key=next(key for key,name in __import__('mta.application.complete_daily_batch_files',fromlist=['PICK_NAMES']).PICK_NAMES.items() if name==filename)
                        with pick_downloads.open_report(run,{},report)[0] as stream:self.assertEqual(stream.read(),expected[key])
                    with patch.object(pick_downloads,'scope',return_value=(set(),set())):
                        with self.assertRaisesRegex(ValueError,'scope_denied'):pick_downloads.open_report(run,{},'LogisticPickListReport')
                    target=Path(td)/str(run.pk)/'download'/'LogisticPickListReport.csv'
                    original=target.read_bytes();target.write_bytes(original+b'tamper')
                    with self.assertRaisesRegex(ValueError,'file_drift'):pick_downloads.open_report(run,{},'LogisticPickListReport')
                    target.unlink()
                    with self.assertRaisesRegex(ValueError,'file_unavailable'):pick_downloads.open_report(run,{},'LogisticPickListReport')
                    target.write_bytes(original)
            print('SECTION9_PICK_THRESHOLDS_PASS '+json.dumps(dict(counts=counts,pins=pins)))


if __name__=='__main__':unittest.main()
