"""Compatible reader commits do not mint database permission; schema still does."""
import os
import unittest
from copy import deepcopy
from unittest.mock import Mock,patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','isolated-schema-admission-test')
import django
django.setup()
from mta.runtime import schema_admission as schema
from mta.serialization import digest


class CompatibleSchemaTests(unittest.TestCase):
    def setUp(self):
        self.cert={'receipt_digest':'a'*64,'authority_roles':['owner','installer','runtime']}
        self.original={'namespace':'owned'}
        self.capability={'release_identity':{'migrations_digest':'b'*64}}
        self.body={'original':'activation'}
        self.cursor=Mock()
        self.enterContext(patch.object(schema,'native_migrations',return_value={}))
        self.enterContext(patch.object(schema,'validate_migration_history'))

    def test_two_code_releases_use_original_schema_and_never_lookup_target_permission(self):
        for commit,manifest in (('1'*40,'2'*64),('3'*40,'4'*64)):
            with self.subTest(commit=commit),patch.object(schema,'original_activation',
                    return_value=(self.cert,self.original,self.capability,self.body)), \
                    patch('mta.runtime.ingestion_admission.validate_activation',return_value=self.cert) as validate, \
                    patch.object(schema,'_record',side_effect=AssertionError('No code-authority lookup')), \
                    patch('mta.runtime.ingestion_authority.append',side_effect=AssertionError('No code-authority append')):
                actual=schema.validate(self.cursor,'owned',dict(source_commit=commit,
                    manifest_sha256=manifest,migrations_digest='b'*64))
                self.assertIs(actual,self.cert)
                validate.assert_called_once_with(self.cursor,self.body)

    def test_unchanged_schema_still_rejects_live_guard_or_foreign_owner_failure(self):
        with patch.object(schema,'original_activation',return_value=(self.cert,self.original,self.capability,self.body)), \
                patch('mta.runtime.ingestion_admission.validate_activation',side_effect=ValueError('live guards differ')):
            with self.assertRaisesRegex(ValueError,'live guards'):
                schema.validate(self.cursor,'owned',dict(migrations_digest='b'*64))

    def test_new_schema_without_a_privileged_migration_receipt_is_unavailable(self):
        with patch.object(schema,'original_activation',return_value=(self.cert,self.original,self.capability,self.body)), \
                patch.object(schema,'_record',return_value=None):
            with self.assertRaisesRegex(ValueError,'explicit upgrade'):
                schema.validate(self.cursor,'owned',dict(migrations_digest='c'*64))

    def test_schema_receipt_is_not_bound_to_later_reader_commits(self):
        record=dict(certification_digest=self.cert['receipt_digest'],
            original_registration_digest=digest(self.original),applied_migrations=[['fresh_mta','new']],
            schema_digest='schema',guard_digest='guard',target_commit='1'*40)
        for commit in ('2'*40,'3'*40):
            with patch.object(schema,'original_activation',return_value=(self.cert,self.original,self.capability,self.body)), \
                    patch.object(schema,'_record',return_value=record), \
                    patch.object(schema,'applied_migrations',return_value=[['fresh_mta','new']]), \
                    patch('release.native_schema.schema_digest',return_value='schema'), \
                    patch('mta.runtime.ingestion_admission.security_digest',return_value='guard'):
                self.assertIs(schema.validate(self.cursor,'owned',dict(source_commit=commit,
                    migrations_digest='c'*64)),self.cert)

    def test_schema_receipt_cannot_borrow_changed_certificate_shape_or_guards(self):
        valid=dict(certification_digest=self.cert['receipt_digest'],
            original_registration_digest=digest(self.original),applied_migrations=[['fresh_mta','new']],
            schema_digest='schema',guard_digest='guard')
        for key in valid:
            record=deepcopy(valid);record[key]='foreign'
            with self.subTest(field=key),patch.object(schema,'original_activation',
                    return_value=(self.cert,self.original,self.capability,self.body)), \
                    patch.object(schema,'_record',return_value=record), \
                    patch.object(schema,'applied_migrations',return_value=[['fresh_mta','new']]), \
                    patch('release.native_schema.schema_digest',return_value='schema'), \
                    patch('mta.runtime.ingestion_admission.security_digest',return_value='guard'):
                with self.assertRaisesRegex(ValueError,'guard contract'):
                    schema.validate(self.cursor,'owned',dict(migrations_digest='c'*64))


class PreservedMetadataTests(unittest.TestCase):
    def test_additive_schema_columns_do_not_rewrite_existing_fields(self):
        from release.upgrade_database import preserved
        before={'accepted':[{'id':'one','Norm':10},{'id':'two','Norm':None}]}
        preserved(before,{'accepted':[{'id':'two','Norm':None,'new':None},
            {'id':'one','Norm':10,'new':None}]})
        for after in ({'accepted':[{'id':'one','Norm':11},{'id':'two','Norm':None}]},
                {'accepted':[{'id':'one','Norm':10}]},
                {'accepted':before['accepted']+[{'id':'three','Norm':10}]}):
            with self.assertRaises(ValueError):preserved(before,after)

    def test_original_metadata_types_and_present_null_fields_cannot_change(self):
        from release.upgrade_database import preserved
        for old,new in ((True,1),(1,1.0),(False,0)):
            with self.subTest(old=old,new=new),self.assertRaises(ValueError):
                preserved({'accepted':[dict(id='one',value=old)]},
                          {'accepted':[dict(id='one',value=new)]})
        with self.assertRaisesRegex(ValueError,'removed accepted metadata fields'):
            preserved({'accepted':[dict(id='one',value=None)]}, {'accepted':[dict(id='one')]})



class MigrationHistoryTests(unittest.TestCase):
    def test_authenticated_prefix_is_allowed_but_unknown_or_missing_migrations_are_not(self):
        files={'mta/runtime/migrations/__init__.py':'0'*64,
            'mta/runtime/migrations/0001_first.py':'1'*64,
            'mta/runtime/migrations/0002_next.py':'2'*64}
        first={k:v for k,v in files.items() if '0002_' not in k}
        with patch.object(schema,'applied_migrations',return_value=[['fresh_mta','0001_first']]):
            schema.validate_migration_history(None,files,digest(first))
            with self.assertRaises(ValueError):schema.validate_migration_history(None,files,digest(files))
        with patch.object(schema,'applied_migrations',return_value=[['fresh_mta','0001_first'],['fresh_mta','unknown']]):
            with self.assertRaises(ValueError):schema.validate_migration_history(None,files,digest(first))
        with patch.object(schema,'applied_migrations',return_value=[['fresh_mta','0001_first'],['fresh_mta','0002_next']]):
            schema.validate_migration_history(None,files,digest(files))
            with self.assertRaises(ValueError):schema.validate_migration_history(None,files,digest(first))
