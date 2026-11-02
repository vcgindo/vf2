"""The upgrade allowance recognizes one exact same-value bootstrap only."""
from copy import deepcopy
from types import SimpleNamespace
import os
import unittest
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'settings-adoption-unit')
import django
django.setup()
from mta.runtime import execution_settings as central
from mta.runtime.execution_setting_catalogue import extract
from mta.runtime.execution_setting_values import rows_digest
from mta.runtime.ingestion_admission import receipt, REVISION_FIELDS
from mta.serialization import digest

MASTERS = 'mta.fresh_mta_masterinputrevision'
STATES = 'mta.fresh_mta_ingestionrevisionstate'
HEADERS = 'mta.fresh_mta_executionsettingsversion'
VALUES = 'mta.fresh_mta_executionsetting'


class AdoptionPreservationTests(unittest.TestCase):
    def fixture(self, empty_tables=False):
        profile = {'delivery': {'batch': {'AutoDBMActive': 0}}}
        owner = SimpleNamespace(pk='owner', configuration_digest=digest(profile))
        cells = extract(profile)
        version = SimpleNamespace(pk='version', initialization_id=owner.pk, revision=1,
            effective_date=None, status='COMMITTED', format_version=1,
            values_digest=rows_digest(cells), profile_digest=digest(profile))
        parent = dict(id='parent', initialization_id=owner.pk, parent_id=None, run_id='accepted-run',
            master_epoch=9, configuration_epoch=11, partitions={'opening_master_root': 'a'*64}, status='ACCEPTED')
        parent['receipt_digest'] = receipt({k:parent[k] for k in REVISION_FIELDS})
        state = dict(initialization_id=owner.pk, master_epoch=9, configuration_epoch=11, fact_epoch=13)
        before = {MASTERS:[parent], STATES:[state], 'immutable-accepted': [{'typed':True,'value':None}]}
        if empty_tables:
            before.update({HEADERS:[], VALUES:[]})
        new = dict(id='new', initialization_id=owner.pk, parent_id='parent', run_id='accepted-run',
            master_epoch=9, configuration_epoch=14,
            partitions={'contract':central.PARTITION_CONTRACT,'settings':central.reference(version)}, status='ACCEPTED')
        new['receipt_digest'] = receipt({k:new[k] for k in REVISION_FIELDS})
        after = deepcopy(before)
        after[MASTERS].append(new); after[STATES][0]['configuration_epoch'] += 3
        after[HEADERS] = [{'id':'version'}]
        after[VALUES] = [{'id':i,'version_id':'version'} for i,_ in enumerate(cells)]
        return owner, profile, cells, version, before, after

    def verify(self, f):
        owner, profile, cells, version, before, after = f
        with patch('mta.runtime.execution_setting_models.ExecutionSettingsVersion.objects.get',return_value=version), \
             patch('release.execution_settings_command.original_profile',return_value=profile), \
             patch('mta.runtime.execution_settings_sources.current_state',return_value={}), \
             patch.object(central,'_rows',return_value=cells), \
             patch.object(central,'validate_revision') as validate:
            result = central.preserved_adoption(owner,before,after)
            validate.assert_called_once()
            return result

    def test_pre_feature_and_same_schema_empty_bootstrap_pass_and_reverify(self):
        for empty in (False,True):
            with self.subTest(empty_tables=empty):
                f = self.fixture(empty)
                self.assertEqual(self.verify(f),central.reference(f[3]))
                self.assertEqual(self.verify(f),central.reference(f[3]))

    def test_candidate_foreign_stale_or_wrong_run_wrapper_denied(self):
        for field, value in [('status','CANDIDATE'),('initialization_id','foreign'),
                             ('parent_id','wrong'),('run_id','wrong'),('master_epoch',10),
                             ('configuration_epoch',15),('receipt_digest','wrong')]:
            with self.subTest(field=field):
                f = self.fixture(); f[-1][MASTERS][-1][field] = value
                with self.assertRaises(ValueError): self.verify(f)

    def test_original_rows_and_unrelated_epochs_or_extra_values_cannot_change(self):
        for change in ('old-master','accepted','fact-epoch','extra-value','foreign-value','extra-header'):
            with self.subTest(change=change):
                f = self.fixture(); after=f[-1]
                if change=='old-master':after[MASTERS][0]['run_id']='wrong'
                elif change=='accepted':after['immutable-accepted'][0]['typed']=1
                elif change=='fact-epoch':after[STATES][0]['fact_epoch']+=1
                elif change=='extra-value':after[VALUES].append({'id':99,'version_id':'version'})
                elif change=='foreign-value':after[VALUES][0]['version_id']='foreign'
                else:after[HEADERS].append({'id':'extra'})
                with self.assertRaises(ValueError):self.verify(f)

    def test_existing_settings_history_never_uses_first_adoption_allowance(self):
        f=self.fixture(True);f[-2][HEADERS]=[{'id':'old-version'}]
        with self.assertRaisesRegex(ValueError,'preexisting settings history'):self.verify(f)

    def test_exact_unchanged_metadata_needs_no_extra_authority(self):
        f=self.fixture(True)
        with patch.object(central,'_rows',side_effect=AssertionError('No value read for unchanged prefix')):
            self.assertIsNone(central.preserved_adoption(f[0],f[-2],deepcopy(f[-2])))


if __name__=='__main__':unittest.main()
