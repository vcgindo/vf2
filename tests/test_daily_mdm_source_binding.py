"""Reject incomplete or cross-artifact MDM ownership before day execution."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from mta.mdm import daily_source as binding
from mta.serialization import digest


class DailySourceBindingTests(unittest.TestCase):
    def source(self):
        families={str(i):dict(owner_digest=str(i)*64) for i in (1,2,3)}
        receipt=dict(schema=binding.SCHEMA, artifact_sha256='a'*64,
            artifact_schema='registered-artifact-v1', adapter_sha256=binding.adapter_digest(),
            families=families,configuration=binding.configuration_digest())
        source=SimpleNamespace(receipt=receipt,digest=digest(receipt),dll_digest=binding.DLL)
        installed=[SimpleNamespace(master_id=i,receipt=families[str(i)],
                    digest=digest(families[str(i)])) for i in (2,3)]
        return source,installed

    def verify(self, source):
        return binding.require_binding(source,artifact_sha256='a'*64,
                                       artifact_schema='registered-artifact-v1')

    def test_exact_artifact_adapter_dll_and_complete_family_binding(self):
        source,installed=self.source()
        with patch.object(binding.MdmFamilySource.objects,'filter',return_value=installed):
            self.assertIs(self.verify(source),source)
            installed[1].digest='changed'
            with self.assertRaisesRegex(ValueError,'family installation identity'):
                self.verify(source)

    def test_cross_artifact_and_incomplete_source_rejected(self):
        for name,value in [('artifact_sha256','b'*64),('artifact_schema','other'),
                           ('adapter_sha256','changed')]:
            with self.subTest(field=name):
                source,_=self.source();source.receipt[name]=value
                source.digest=digest(source.receipt)
                with self.assertRaisesRegex(ValueError,'not bound'):
                    self.verify(source)
        source,_=self.source();source.dll_digest='other'
        with self.assertRaisesRegex(ValueError,'DLL'):
            self.verify(source)
        source,_=self.source()
        with patch.object(binding,'configuration_digest',return_value={'changed':'config'}), \
                self.assertRaisesRegex(ValueError,'configuration differs'):
            self.verify(source)
        source,_=self.source()
        with patch.object(binding.MdmFamilySource.objects,'filter',return_value=[]), \
                self.assertRaisesRegex(ValueError,'not installed'):
            self.verify(source)
