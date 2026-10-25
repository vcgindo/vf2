"""One stdlib codec serves auth and MTA with the retained phase wire contract."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from uuid import uuid4

from release import phase_selection as contract
from mta.presentation import scoped_selection
from mta.serialization import digest


def anchor():
    value={name:'a'*64 for name in contract.FIELDS}
    value.update(schema=contract.SCHEMA,run_id=str(uuid4()),phase_id=str(uuid4()),business_date='2037-04-10')
    value['selection_digest']=digest({k:v for k,v in value.items() if k!='selection_digest'})
    return value


class PhaseSelectionContractTests(unittest.TestCase):
    def test_mta_and_auth_share_exact_codec_and_original_canonical_checksum(self):
        self.assertIs(scoped_selection.validate,contract.validate)
        self.assertIs(scoped_selection.read,contract.read)
        value=anchor()
        for key in ('run_id','phase_id'):
            value[key]=value[key].upper()  # Retain original UUID parser acceptance.
        value['selection_digest']=digest({k:v for k,v in value.items() if k!='selection_digest'})
        self.assertEqual(contract.decode(json.dumps(value).encode()),value)
        self.assertEqual(value['selection_digest'],hashlib.sha256(json.dumps(
            {k:v for k,v in value.items() if k!='selection_digest'},sort_keys=True,
            ensure_ascii=True,separators=(',',':'),allow_nan=False).encode()).hexdigest())

    def test_codec_import_and_validation_require_no_mta_django_or_database(self):
        script="""import json,runpy,sys
codec=runpy.run_path(sys.argv[1])
value=json.loads(sys.stdin.read())
assert codec['validate'](value)==value
assert not any(n=='django' or n.startswith(('django.','mta.')) for n in sys.modules)
print('STDLIB_ONLY_PHASE_CODEC_PASS')
"""
        result=subprocess.run([sys.executable,'-I','-c',script,str(Path(contract.__file__).resolve())],
            input=json.dumps(anchor()),text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'STDLIB_ONLY_PHASE_CODEC_PASS')
