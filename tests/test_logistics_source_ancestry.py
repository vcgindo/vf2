"""Adversarial checks for the existing native source-inverse mechanism."""
import json
import tempfile
from pathlib import Path
from unittest import TestCase, mock
from mta.mdm import native_report_compatibility as c
from mta.serialization import digest


class LogisticsSourceAncestryTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.prior={'a.py':b'prior\n','same.py':b'same\n'}
        self.current={'a.py':b'prior\n# serving connection\n','same.py':b'same\n','new.py':b'new\n'}
        for n,raw in self.current.items():(self.root/n).write_bytes(raw)
        self.files={n:c._sha(raw) for n,raw in self.current.items()}
        identity=dict(adapter_digest='a'*64,closing_projection_version=c.VERSION,
                      source_manifest_digest=digest(self.files))
        self.identity=identity
        self.v8=json.dumps({'current_files':{n:c._sha(raw) for n,raw in self.prior.items()},
                            'current_identity':dict(identity,adapter_digest='b'*64)}).encode()
        self.value=dict(schema=c.LOGISTICS_SCHEMA,v8_sha256=c._sha(self.v8),
            current_files=self.files,current_identity=identity,
            inverse={n:c.inverse_delta(self.prior.get(n,b''),self.current[n]) for n in ('a.py','new.py')})
        self.patch=mock.patch.multiple(c,LOGISTICS_FILES={'a.py','new.py'},LOGISTICS_V8_SHA256=c._sha(self.v8))
        self.patch.start();self.addCleanup(self.patch.stop)

    def validate(self,value=None,**kw):
        raw=json.dumps(self.value if value is None else value).encode()
        args=dict(raw=raw,pin=c._sha(raw),v8_raw=self.v8,root=self.root,files=self.files,identity=self.identity)
        args.update(kw)
        return c.validate_logistics_ancestry(**args)

    def test_exact_inverse_retains_all_prior_files_and_identity(self):
        files,overrides,identity=self.validate()
        self.assertEqual(files,{n:c._sha(raw) for n,raw in self.prior.items()})
        self.assertEqual(overrides,{'a.py':b'prior\n'})
        self.assertEqual(identity,json.loads(self.v8)['current_identity'])

    def test_bad_pins_roster_identity_and_bytes_are_rejected(self):
        for kwargs in [dict(pin='0'*64),dict(v8_raw=b'{}'),
                       dict(files={**self.files,'extra.py':'0'*64}),
                       dict(identity={**self.identity,'adapter_digest':'0'*64})]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.validate(**kwargs)
        (self.root/'a.py').write_bytes(b'changed on disk')
        with self.assertRaises(ValueError):self.validate()

    def test_re_pinned_declaration_cannot_remove_old_source_or_keep_added_bytes(self):
        import copy
        for name in ('a.py','new.py'):
            value=copy.deepcopy(self.value)
            value['inverse'][name]=[]
            with self.subTest(name=name),self.assertRaises(ValueError):self.validate(value)
        value=copy.deepcopy(self.value);value['inverse'].pop('new.py')
        with self.assertRaises(ValueError):self.validate(value)
        value=copy.deepcopy(self.value);value['schema']='generic-source-bypass'
        with self.assertRaises(ValueError):self.validate(value)
