"""An explicit successor can change the report image, never selection or capacity."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import stage2_identity_catalogue as catalogue
from tools import stage2_report_contention_runtime as runtime


class CatalogueCheckpointTests(unittest.TestCase):
    def check(self, successor):
        original = dict(protected={'accepted': 'fixed'}, mta={'image': 'old', 'environment_sha256': 'fixed', 'memory': 4}, ready={'fixture': 'fixed'})
        selected = dict(environment={}, volumes=[])
        files = {'after.json': original, 'before.json': {'selection': selected},
                 **{'compose.'+name+'.json': {'services': {'user-service': selected}}
                    for name in ('candidate', 'normal')}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'checkpoint.json';path.write_text(json.dumps(successor))
            with patch.object(catalogue, 'saved', side_effect=files.__getitem__), \
                 patch.object(catalogue.window, 'protected', return_value=successor['protected']), \
                 patch.object(catalogue.window, 'inspect'), \
                 patch.object(catalogue.window, 'runtime', return_value=successor['mta']), \
                 patch.object(catalogue, 'live_selection', return_value=selected), \
                 patch.object(catalogue, 'gateway_selection', return_value=selected), \
                 patch.object(catalogue, 'selection', return_value=selected):
                catalogue.check_current(path)

    def test_image_only_successor_keeps_restoration_available(self):
        self.check(dict(protected={'accepted': 'fixed'}, mta={'image': 'new', 'environment_sha256': 'fixed', 'memory': 4}, ready={'fixture': 'fixed'}))

    def test_successor_cannot_change_binding_capacity_or_protected_identity(self):
        base = dict(protected={'accepted': 'fixed'}, mta={'image': 'new', 'environment_sha256': 'fixed', 'memory': 4}, ready={'fixture': 'fixed'})
        for owner, key, value in [('mta','environment_sha256','changed'),('mta','memory',8),('protected','accepted','changed'),('ready','fixture','changed')]:
            with self.subTest(owner=owner,key=key):
                candidate=copy.deepcopy(base);candidate[owner][key]=value
                with self.assertRaisesRegex(ValueError,'more than the MTA image'):
                    self.check(candidate)

    def test_failed_candidate_can_roll_back_without_candidate_readiness(self):
        files = {'deployment.json': dict(candidate_image='candidate',rollback_image='baseline',
                    fixture_compose_sha256='fixed',selection={'catalogue':'fixed'}),
                 'before.json': {'protected': {'accepted':'fixed'}},
                 'compose.rollback.json': {'services': {'mta': {'image':'baseline'}}}}
        with patch.object(runtime,'saved',side_effect=files.__getitem__), \
             patch.object(runtime.window,'inspect',return_value={'Image':'candidate'}), \
             patch.object(runtime.window,'protected',return_value={'accepted':'fixed'}), \
             patch.object(runtime.window,'sha',return_value='fixed'), \
             patch.object(runtime.window,'runtime',return_value={'image':'candidate','environment_sha256':'unexpected'}), \
             patch.object(runtime.catalogue,'gateway_selection',return_value={'catalogue':'fixed'}), \
             patch.object(runtime,'write'), patch.object(runtime.subprocess,'run') as compose, \
             patch.object(runtime,'verify_runtime',return_value={'restored':True}) as verify:
            runtime.deploy(rollback=True)
        compose.assert_called_once()
        verify.assert_called_once_with('baseline')
