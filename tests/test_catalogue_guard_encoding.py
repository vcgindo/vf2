"""Exact finite catalogue encoding; no general state serializer replacement."""
import os,unittest
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django;django.setup()
from mta.serialization import digest
from mta.presentation.report_verification import _catalogue_digest
class CatalogueEncodingTests(unittest.TestCase):
    def test_identical_canonical_hashes_for_catalogue_builtin_types(self):
        values=[None,(),[],(True,False,None,2**63-1,-1),
                ('unicode: \u0915\u092e\u0930 \U0001f600','quotes"\\\t\n'),
                (('db','owner','read committed'),[[(321,'900'),(321,'900')]],
                 [('reader',False,True,None,['search_path=mta,public'])],[])]
        for value in values:
            with self.subTest(value=value):self.assertEqual(_catalogue_digest(value),digest(value))
    def test_rejects_noncanonical_nonfinite_values(self):
        for value in (float('nan'),float('inf')):
            with self.assertRaises(ValueError):_catalogue_digest(value)
if __name__=='__main__':unittest.main()
