"""Approved finite Windows-1252 descriptions; identifiers stay ASCII.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
import unittest

from mta.application.r1_importer_master import _typed_row, _distinct, process_importer_master
from tests.test_production_csv_diagnostics import master_payload


class ImporterDescriptionTextTests(unittest.TestCase):
    def test_original_characters_survive_complete_master_processing(self):
        for text in ('Gulf\u00a0Oil', 'Gulf\u00ae Oil', 'Gulf\u2013Oil', 'Gulf\u00a0\u00ae\u2013Oil'):
            with self.subTest(text=text):
                payload=master_payload()
                before=deepcopy(payload)
                for row in payload['raw_master']:
                    row['SKUDescription']=text
                result=process_importer_master(payload)
                self.assertEqual(result['outcome'], 'APPLIED')
                self.assertTrue(result['tables']['SKUDescriptionTbl'])
                self.assertTrue(all(r['SKUDescription']==text for r in result['tables']['SKUDescriptionTbl']))
                self.assertEqual(before['prior'], payload['prior'])

    def test_only_descriptions_gain_exact_three_characters(self):
        for char in ('\u00a0','\u00ae','\u2013'):
            for field in ('SKUDescription','WHDescription','ParentDescription'):
                self.assertEqual(_typed_row({field:'x'+char+'y'},(field,)),{field:'x'+char+'y'})
            for field in ('SKUCode','WhCode','ParentWhCode','SL1','LL1','SKUAtt01','RequestedBy'):
                with self.subTest(char=char,field=field), self.assertRaises(ValueError):
                    _typed_row({field:'x'+char+'y'},(field,))

    def test_other_unicode_and_existing_length_limits_still_reject(self):
        for text in ('caf\u00e9','\u4e2d','x\u00a9','x'*126):
            with self.subTest(text=text),self.assertRaises(ValueError):
                _typed_row({'SKUDescription':text},('SKUDescription',))
        self.assertEqual(_typed_row({'SKUDescription':'\u00ae'*125},('SKUDescription',)),
                         {'SKUDescription':'\u00ae'*125})

    def test_exact_characters_nulls_and_duplicate_description_occurrences(self):
        fields=('SKUCode','SKUDescription')
        rows=[dict(SKUCode='S',SKUDescription='A\u00a0B'),
              dict(SKUCode='S',SKUDescription='A B'),
              dict(SKUCode='S',SKUDescription='A\u00a0B')]
        self.assertEqual(_distinct(rows,fields),rows[:2])
        self.assertEqual(_typed_row({'SKUDescription':None},('SKUDescription',)),{'SKUDescription':None})


if __name__=='__main__':unittest.main()
