"""Real local file observations with native fullkit outcomes; no DB proof."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mta.application import literal_fullkit as subject
from mta.application.operational_alert_files import unavailable_daily_bytes


class LiteralFullkitTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='fullkit-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.inputs=self.root/'input';self.inputs.mkdir()
        self.site=self.root/'site';self.site.mkdir()
        (self.inputs/'present.csv').write_bytes(b'SKU,Qty\r\nP1,2\r\n')
        self.rows=[dict(Id=i,Path=str(self.inputs),FileName=name,Type='DataFiles',
            Exists=True,ResolvedPath='stale',ResolvedFileName='stale')
            for i,name in ((7,'present.csv'),(2,'absent.csv'),(9,'absent.csv'))]
        self.settings=[dict(Parameter='FullkitAvailable',Value='old'),
            dict(Parameter='FullkitCheckdate',Value='old'),dict(Parameter='Other',Value='unchanged')]
        self.opening=[dict(FileId=44,RunDateTime='2026-10-25T00:00:00',Reason='earlier real failure')]

    def config(self):
        return subject.configuration(critical_files=self.rows,settings=self.settings,
            abort_opening=self.opening,input_root=self.inputs,site_root=self.site)

    def check(self,config=None):
        return subject.check(self.config() if config is None else config,business_date='2026-10-26',
            run_datetime='2026-10-26T10:15:00',capture_root=self.root/'capture')

    def test_actual_missing_files_native_order_duplicate_reasons_and_frozen_original(self):
        original=deepcopy((self.rows,self.settings,self.opening))
        result=self.check()
        self.assertTrue(result['AbortRun']);self.assertTrue(result['daily_unavailability_alert_required'])
        self.assertEqual([row['Exists'] for row in result['CriticalFiles']],[True,False,False])
        self.assertEqual([row['Value'] for row in result['ImporterSettingsTbl']],['0','2026-10-26','unchanged'])
        reason=f'File "absent.csv" is not present at Location "{self.inputs}".'
        self.assertEqual(result['RunAbortReasons'],self.opening+[
            dict(FileId=i,RunDateTime='2026-10-26T10:15:00.000',Reason=reason) for i in (2,9)])
        self.assertEqual((self.rows,self.settings,self.opening),original)
        observed=result['observations']
        self.assertEqual([row['file_id'] for row in observed],[7,2,9])
        payload=(self.inputs/'present.csv').read_bytes()
        self.assertEqual((self.root/'capture'/observed[0]['member']).read_bytes(),payload)
        self.assertEqual(observed[0]['sha256'],sha256(payload).hexdigest())
        self.assertEqual(observed[0]['size_bytes'],len(payload))
        self.assertIsNone(observed[1]['member']);self.assertIsNone(observed[1]['sha256'])
        report=unavailable_daily_bytes(result['RunAbortReasons'],result['clock'])
        self.assertEqual(report.count(b'absent.csv'),2)
        self.assertNotIn(b'earlier real failure',report)

    def test_available_inputs_keep_native_success_and_missing_settings_missing(self):
        (self.inputs/'absent.csv').write_bytes(b'')
        self.settings=[]
        result=self.check()
        self.assertFalse(result['AbortRun']);self.assertFalse(result['daily_unavailability_alert_required'])
        self.assertEqual(result['ImporterSettingsTbl'],[])
        self.assertEqual(result['RunAbortReasons'],self.opening)
        self.assertEqual([row['size_bytes'] for row in result['observations']][1:],[0,0])

    def test_hooks_expansion_goahead_and_outside_roots_refuse_before_capture(self):
        changes=('hook','goahead','expansion','outside','traversal','alias','duplicate_id','null_setting')
        for change in changes:
            rows=deepcopy(self.rows);settings=deepcopy(self.settings)
            if change=='hook':(self.site/subject.HOOKS[0]).write_text('not executed')
            if change=='goahead':rows[0]['Type']='GoAheadFiles'
            if change=='expansion':rows[0]['Path']='%ROOT%'
            if change=='outside':rows[0]['Path']=str(self.root)
            if change=='traversal':rows[0]['Path']=str(self.inputs/'..'/'input')
            if change=='alias':rows[0]['FileName']='*.csv'
            if change=='duplicate_id':rows[1]['Id']=rows[0]['Id']
            if change=='null_setting':settings[0]['Value']=None
            with self.subTest(change=change),self.assertRaises(ValueError):
                subject.configuration(critical_files=rows,settings=settings,abort_opening=self.opening,
                    input_root=self.inputs,site_root=self.site)
            (self.site/subject.HOOKS[0]).unlink(missing_ok=True)
            self.assertFalse((self.root/'capture').exists())

    def test_settings_native_widths_and_no_implicit_empty_opening(self):
        self.settings[2]['Value']='x'*5000
        self.assertEqual(self.config()['ImporterSettingsTbl'][2]['Value'],'x'*5000)
        self.settings[0]['Parameter']='x'*51
        with self.assertRaises(ValueError):self.config()
        self.settings=[];self.opening=None
        with self.assertRaises(ValueError):self.config()

    def test_new_hook_or_directory_cannot_be_reported_as_missing_file(self):
        config=self.config()
        (self.site/subject.HOOKS[1]).write_text('unexpected')
        with self.assertRaises(ValueError):self.check(config)
        (self.site/subject.HOOKS[1]).unlink()
        (self.inputs/'absent.csv').mkdir()
        with self.assertRaises(ValueError):self.check(config)
        # Preserved first original remains; incomplete capture is not success.
        self.assertTrue((self.root/'capture'/'00000000-present.csv').exists())

    def test_changed_observation_refuses_and_keeps_original_bytes(self):
        real_capture=subject._capture
        def changed(*args):
            value=real_capture(*args)
            (self.inputs/'present.csv').unlink()
            return value
        with patch.object(subject,'_capture',side_effect=changed),self.assertRaises(ValueError):
            self.check()
        self.assertTrue((self.root/'capture'/'00000000-present.csv').exists())

    def test_original_root_never_used_for_custody_and_wrong_clock_refuses(self):
        config=self.config()
        for root,clock in ((self.inputs/'capture','2026-10-26T10:15:00'),
                           (self.root/'capture','2026-10-25T10:15:00')):
            with self.subTest(root=root,clock=clock),self.assertRaises(ValueError):
                subject.check(config,business_date='2026-10-26',run_datetime=clock,capture_root=root)
        self.assertTrue((self.inputs/'present.csv').exists())

    def test_canonical_batch_and_sql_pins_match_retained_manifest(self):
        manifest=json.loads((Path(__file__).resolve().parents[1]/'baseline/manifest.json').read_bytes())
        pins={row['path'].split('/mta-engine/',1)[-1]:row['sha256'] for row in manifest['engine_sources']}
        self.assertEqual({key:pins[key] for key in subject.SOURCES},subject.SOURCES)
