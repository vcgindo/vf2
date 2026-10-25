"""BPR dependencies accept only the explicit UptoDBM request contract."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tests.test_scope_runtime_reports import reference
from tests.test_production_upto_dbm import dispositions


class ScopedUptoDbmConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY','local-unit-check-only')
        import django
        django.setup()

    def test_bpr_and_dbm_pairings_are_distinct_and_reader_does_not_re_admit_calculation_release(self):
        from mta.presentation.scoped_view import _configuration
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.production_scope import CONFIGURED_SCHEMA
        from mta.runtime.production_upto_dbm import SCHEMA
        from mta.serialization import digest
        base = dict(schema=CONFIGURED_SCHEMA,scope='UptoBPR',command_key='read-contract',
            compatibility_digest='a'*64,runtime_reports=reference())
        dbm = dict(base,schema=SCHEMA,scope='UptoDBM',dispositions=dispositions())
        with patch('mta.runtime.scope_runtime_reports.require_test_database'), \
                patch('mta.runtime.input_reader.read_input') as read, \
                patch('release.native_identity.require_current',side_effect=AssertionError('Reader command recertification')):
            for value in (base,dbm):
                read.return_value = dict(scope_request=deepcopy(value))
                self.assertEqual(_configuration(SimpleNamespace()),(reference(),digest(value)))
            invalid = [dict(dbm,schema=CONFIGURED_SCHEMA),dict(base,schema=SCHEMA),
                dict(base,scope='UptoDBM'),dict(dbm,extra=True),dict(dbm,dispositions={})]
            for value in invalid:
                read.return_value = dict(scope_request=value)
                with self.subTest(value=value),self.assertRaises(PublicationUnavailable):
                    _configuration(SimpleNamespace())


if __name__=='__main__': unittest.main()
