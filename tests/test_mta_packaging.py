"""Focused file/build admission checks; fake wheel transport, no Docker or database.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from release import native_identity as identity
from release import mta_packaging as packaging
from release.build_mta import build


class MtaPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work=Path(self.temporary.name)
        self.root=self.work/'source'
        self.wheels=self.work/'wheels';self.wheels.mkdir()
        self.commit='a'*40
        repository=Path(__file__).resolve().parents[1]
        contents={name:(repository/name).read_bytes() for name in identity.MTA_RELEASE_FILES}
        contents.update({
            'manage.py':b'# command entry\n','requirements.txt':b'Django==5.2.17\n',
            'mta/mdm/initialization.py':b"IMPLEMENTATION_FILES = ('mdm/initialization.py',)\n",
            'mta/runtime/migrations/0142_native_evidence_default.py':b'# native schema history\n',
            'vectorflow/settings.py':b'# settings\n',
            'baseline/operational-alert-source-pins.json':b'{"pins":[]}\n',
            'release/mta_packaging.py':(repository/'release/mta_packaging.py').read_bytes(),
            'frontend/src/unchanged.ts':b'// original frontend bytes\n',
            'mto/mto_app/unchanged.py':b'# original MTO bytes\n',
            'user-service/apps/unchanged.py':b'# original auth bytes\n',
        })
        descriptor=json.loads(contents['release/mta-wheels.lock.json'])
        for index,row in enumerate(descriptor['files']):
            raw=('transport fixture '+str(index)).encode()
            (self.wheels/row['filename']).write_bytes(raw)
            row['sha256']=hashlib.sha256(raw).hexdigest();row['bytes']=len(raw)
        contents['release/mta-wheels.lock.json']=json.dumps(descriptor).encode()
        for name,raw in contents.items():
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        self.full=dict(schema='vectorflow-release-source-v1',source_commit=self.commit,
            default_data_import=False,files={name:hashlib.sha256(raw).hexdigest() for name,raw in contents.items()})
        self.native=identity.declaration(self.root,self.commit,self.full['files'])
        (self.root/'release-source.json').write_text(json.dumps(self.full))
        (self.root/identity.MANIFEST).write_text(json.dumps(self.native))
        self.pins=dict(commit=self.commit,source_sha256=packaging.sha(self.root/'release-source.json'),
            native_sha256=packaging.sha(self.root/identity.MANIFEST))
        self.runner=Mock(return_value=SimpleNamespace(returncode=0))

    def build(self,**pins):
        return build(self.root,self.work/'context',self.wheels,image='vectorflow/mta:unit',
            runner=self.runner,**{**self.pins,**pins})

    def test_positive_context_has_exact_native_roster_without_operator_or_other_apps(self):
        value=self.build()
        self.assertEqual(value['status'],'MTA_IMAGE_BUILD_COMPLETED_INSPECTION_STILL_REQUIRED')
        actual=packaging.files(self.work/'context/application')
        self.assertEqual(set(actual),set(self.native['files'])|{identity.MANIFEST})
        self.assertFalse(any(n.startswith(('frontend/','mto/','user-service/')) for n in actual))
        self.assertNotIn('release/mta_packaging.py',actual)
        self.assertNotIn('release/optional_initialize.py',actual)
        args=self.runner.call_args.args[0]
        self.assertIn('--network=none',args)
        self.assertIn('--rm=true',args)
        self.assertIn('--force-rm',args)
        self.assertNotIn('--rm=false',args)
        self.assertFalse(any(arg.startswith(('--memory','--cpu-')) for arg in args))
        self.assertEqual(self.runner.call_args.kwargs['env']['DOCKER_BUILDKIT'],'0')

    def test_raw_checkout_rejected_before_docker(self):
        (self.root/'release-source.json').unlink()
        with self.assertRaises((OSError,ValueError)):self.build()
        self.runner.assert_not_called()

    def test_bad_independent_source_native_or_commit_pin_rejected_before_docker(self):
        for key,value in (('source_sha256','0'*64),('native_sha256','0'*64),('commit','b'*40)):
            with self.subTest(key=key),self.assertRaises(ValueError):self.build(**{key:value})
        self.runner.assert_not_called()

    def test_changed_required_bytes_and_missing_alert_resource_rejected_before_docker(self):
        (self.root/'manage.py').write_text('# changed')
        with self.assertRaises(ValueError):self.build()
        (self.root/'manage.py').write_bytes(b'# command entry\n')
        (self.root/'baseline/operational-alert-source-pins.json').unlink()
        with self.assertRaises(ValueError):self.build()
        self.runner.assert_not_called()

    def test_extra_module_command_and_bytecode_rejected_before_docker(self):
        for name in ('parity/runner.py','mta/runtime/management/commands/record_parity.py',
                     'mta/unapproved.py','injected.pyc'):
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'extra')
            with self.subTest(name=name),self.assertRaises(ValueError):self.build()
            path.unlink()
        self.runner.assert_not_called()

    def test_self_consistent_replacement_descriptor_does_not_supply_authority(self):
        (self.root/'manage.py').write_bytes(b'# substituted')
        self.full['files']['manage.py']=packaging.sha(self.root/'manage.py')
        (self.root/'release-source.json').write_text(json.dumps(self.full))
        with self.assertRaises(ValueError):self.build()
        self.runner.assert_not_called()

    def test_corrupt_but_pinned_schema_descriptor_rejected(self):
        self.full['schema']='unapproved-schema'
        (self.root/'release-source.json').write_text(json.dumps(self.full))
        with self.assertRaises(ValueError):self.build(source_sha256=packaging.sha(self.root/'release-source.json'))
        self.runner.assert_not_called()

    def test_wheel_omission_change_or_extra_dependency_rejected_before_docker(self):
        first=next(self.wheels.iterdir());raw=first.read_bytes()
        first.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.build()
        first.unlink()
        with self.assertRaises(ValueError):self.build()
        first.write_bytes(raw)
        (self.wheels/'unapproved.whl').write_bytes(b'extra')
        with self.assertRaises(ValueError):self.build()
        self.runner.assert_not_called()

    def test_optional_adapters_excluded_from_default_export(self):
        from release.export import included
        self.assertFalse(included('release/optional_initialize.py'))
        self.assertFalse(included('release/optional-initialization.json'))

    def test_current_source_rejects_existing_destination(self):
        (self.work/'context').mkdir()
        with self.assertRaises(ValueError):self.build()
        self.runner.assert_not_called()
