"""Force-source validation across the actual typed reader's size boundary."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'force-readback-unit-only')
import django
django.setup()

from copy import deepcopy
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mta.row_sequences import RecordRows
from mta.serialization import digest
from mta.runtime import operational_force_source as force
from mta.runtime import relational_state


class ForceReadbackTests(unittest.TestCase):
    def populations(self, count):
        # Deliberate duplicate keys, NULLs and occurrence-dependent values.
        return dict(ForceNormChange=[], DBMMaster=[
            dict(SKUCode='S'+str(i % 3), WhCode='L', Norm=None if i % 7 == 0 else i)
            for i in range(count)], MasterDataRaw=[dict(SKUCode='S', WhCode='L', Norm=0)])

    def source(self, rows):
        return SimpleNamespace(run=object(), policy=force.FORCE_CAPTURE_POLICY,
            rows_digest=digest(rows), images={name:dict(image='operational/force/'+name,
                table=table, count=len(rows[name])) for name, table in force.BINDINGS.items()})

    @contextmanager
    def read(self, source, rows):
        def records(run, item):
            self.assertIs(run, source.run)
            return iter(rows[item['image'].rsplit('/', 1)[1]])
        # Stub only the SQL row transport; use the production size-switching
        # reader, real disk spool, force-source ownership and full digest checks.
        with patch.object(relational_state, 'iter_image', side_effect=records):
            yield force._rows(source)

    def test_real_reader_both_sides_of_threshold_and_readonly_mode(self):
        for count in (10000, 10001):
            for spool in (False, True):
                with self.subTest(count=count, spool=spool), TemporaryDirectory() as root:
                    with patch.dict(os.environ, {'VF_WORK_ROOT': root if spool else ''}):
                        expected=self.populations(count)
                        source=self.source(expected)
                        with self.read(source, expected) as actual:
                            self.assertEqual(actual, expected)
                            self.assertEqual(digest(actual), source.rows_digest)
                            self.assertEqual(isinstance(actual['DBMMaster'], RecordRows), count > 10000)
                            if spool and count > 10000:
                                self.assertTrue(actual['DBMMaster']._data.is_file())
                            self.assertEqual(list(actual['DBMMaster']), expected['DBMMaster'])

    def test_closed_population_and_field_contract_remains_enforced(self):
        valid=self.populations(2)
        for value in (None, tuple(valid['DBMMaster']), iter(valid['DBMMaster']), {}):
            with self.subTest(value=type(value).__name__):
                with self.assertRaisesRegex(ValueError, 'Explicit force source populations'):
                    force._validate(dict(valid, DBMMaster=value))
        with self.assertRaisesRegex(ValueError, 'All three'):
            force._validate({'DBMMaster': []})
        for row in (dict(SKUCode='S', WhCode='L'),
                    dict(SKUCode='S', skucode='S', WhCode='L', Norm=0)):
            with self.subTest(row=row):
                with self.assertRaisesRegex(ValueError, 'required fields'):
                    force._validate(dict(valid, DBMMaster=RecordRows.from_rows([row])))
        with self.assertRaisesRegex(ValueError, 'row mapping'):
            force._validate(dict(valid, DBMMaster=[None]))
        with self.assertRaisesRegex(ValueError, 'retain records'):
            force._validate(dict(valid, DBMMaster=RecordRows(1, lambda: iter([None]))))

    def test_large_readback_rejects_value_order_and_multiplicity_drift(self):
        expected=self.populations(10001)
        source=self.source(expected)
        for change in ('value', 'order', 'duplicate'):
            changed=deepcopy(expected)
            if change == 'value': changed['DBMMaster'][-1]['Norm']=-1
            elif change == 'order': changed['DBMMaster'].reverse()
            else: changed['DBMMaster'].append(dict(changed['DBMMaster'][0]))
            # Keep the reader's declared count consistent so the test isolates
            # the force-source full-content digest, not SQL transport checks.
            changed_source=self.source(changed)
            changed_source.rows_digest=source.rows_digest
            with self.subTest(change=change), TemporaryDirectory() as root:
                with patch.dict(os.environ, {'VF_WORK_ROOT': root}):
                    with self.assertRaisesRegex(ValueError, 'values/order differ'):
                        with self.read(changed_source, changed): pass

    def test_source_policy_and_image_ownership_still_denied(self):
        expected=self.populations(1)
        for change in ('policy', 'owner'):
            source=self.source(expected)
            if change == 'policy': source.policy='unapproved'
            else: source.images['DBMMaster']['table']='Importer/MasterDataRaw'
            with self.subTest(change=change), patch.object(force, 'load_image') as reader:
                with self.assertRaises(ValueError): force._rows(source)
                reader.assert_not_called()
