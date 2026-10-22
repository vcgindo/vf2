"""Exact fifth guard admission; existing unapproved fifth/sixth DDL stays denied."""
from copy import deepcopy
import hashlib
from importlib import import_module
from pathlib import Path
import unittest
from unittest.mock import patch
from tests.test_code_schema_inheritance import CodeSchemaCompositionTests
from mta.runtime import ingestion_admission as admission,ingestion_authority as authority
from mta.runtime import report_guard_transition as guard
from mta.serialization import digest


class ReportGuardTransitionTests(unittest.TestCase):
    def test_exact_frozen_guard_recognition_retains_all_metadata_denials(self):
        from mta.runtime.ingestion_ownership import is_revision_guard
        migration=import_module('mta.runtime.migrations.'+guard.MIGRATION_NAME)
        candidate=dict(name='mta.ingestion_watch()',security_definer=True,
            configuration=['search_path=pg_catalog, mta'],returns='trigger')
        for body in (migration.OLD_INGESTION,migration.NEW_INGESTION):
            self.assertTrue(is_revision_guard(dict(candidate,body=body)))
        candidate['body']=migration.NEW_INGESTION
        for field,value in (('body',candidate['body']+'\n'),('name','mta.other()'),
                ('security_definer',False),('configuration',['search_path=public, mta']),
                ('configuration',None),('returns','text')):
            with self.subTest(field=field,value=value if field!='body' else 'mutated'):
                self.assertFalse(is_revision_guard({**candidate,field:value}))

    def fixture(self):
        f=CodeSchemaCompositionTests();f.setUp()
        fourth=f.links[f.latest['target_release']]
        fourth.update(schema_digest=guard.BEFORE_SCHEMA,guard_digest=guard.BEFORE_GUARD)
        code=f.code('a',f.latest,4)
        link=f.links.pop(code['target_release']);f.bodies.pop(code['target_release'])
        code['target_release']=guard.PREVIOUS_RELEASE
        link.update(schema_digest=guard.BEFORE_SCHEMA,guard_digest=guard.BEFORE_GUARD)
        f.bodies[code['target_release']]=code;f.links[code['target_release']]=link
        target=f.schema('b',code,5)
        extension=f.links[target['target_release']]
        extension.update(migration_pins=guard.migration_pins(),catalogue_delta_digest=digest(guard.catalogue_delta()),
            before_schema_digest=guard.BEFORE_SCHEMA,before_guard_digest=guard.BEFORE_GUARD)
        return f,target,extension

    def test_exact_released_guard_after_four_and_code_anchor_is_admitted(self):
        f,target,extension=self.fixture()
        self.assertTrue(guard.approved_receipt(extension))
        self.assertEqual(f.resolve(target)[1:4],(target,'s5','g5'))
        later=f.code('c',target,5)
        self.assertEqual(f.resolve(later)[1:4],(target,'s5','g5'))
        sixth=f.schema('d',later,6)
        with self.assertRaisesRegex(ValueError,'four-admission boundary'):f.resolve(sixth)

    def test_any_other_guard_delta_predecessor_or_bytes_fail_closed(self):
        f,target,extension=self.fixture();original=deepcopy(extension)
        for field,value in (('migration_pins',[[guard.MIGRATION_NAME,'0'*64]]),
                ('catalogue_delta_digest','0'*64),('before_schema_digest','0'*64),
                ('before_guard_digest','0'*64),('previous_release','0'*64)):
            extension.update(original);extension[field]=value
            self.assertFalse(guard.approved_receipt(extension))
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'Exact released report guard'):
                f.resolve(target)
        extension.update(original)
        extension['migration_pins']=[['0169_other','0'*64]]
        with self.assertRaisesRegex(ValueError,'four-admission boundary'):f.resolve(target)

    def test_pinned_migration_bytes_and_complete_delta_exact(self):
        m=import_module('mta.runtime.migrations.'+guard.MIGRATION_NAME)
        raw=Path(m.__file__).read_bytes().replace(b'\r\n',b'\n')
        self.assertEqual(hashlib.sha256(raw).hexdigest(),guard.MIGRATION_SHA256)
        delta=guard.catalogue_delta()
        self.assertEqual(set(delta),{'functions:mta.ingestion_watch()','functions:mta.guard_v3_derived_report_rows()'})
        for change in delta.values():
            self.assertEqual({k:v for k,v in change['before'].items() if k!='body'},
                {k:v for k,v in change['after'].items() if k!='body'})
        self.assertIn('FOR UPDATE OF G;',m.NEW_DERIVED)
        self.assertEqual(m.OLD_INGESTION[m.OLD_INGESTION.index(" IF kind='immutable'"):],
            m.NEW_INGESTION[m.NEW_INGESTION.index(" IF kind='immutable'"):])
        spec=dict(migration_pins=guard.migration_pins(),catalogue_delta=delta,
            previous_release={'manifest_sha256':guard.PREVIOUS_RELEASE})
        guard.require_specification(spec)
        for altered in ({**spec,'migration_pins':[]},{**spec,'catalogue_delta':{}},
                {**spec,'previous_release':{'manifest_sha256':'0'*64}}):
            with self.assertRaisesRegex(ValueError,'exact released'):guard.require_specification(altered)
