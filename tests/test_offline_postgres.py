"""Migration-enabled PostgreSQL guard proof, explicitly invoked in an owned test DB."""
import os
import unittest
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','offline-unit-test')
import django
django.setup()
from django.db import connection, transaction, DatabaseError
from django.test import TransactionTestCase


@unittest.skipUnless(os.environ.get('VFTEST_OFFLINE_POSTGRES')=='1','Explicit owned PostgreSQL proof only')
class OfflinePostgresTests(TransactionTestCase):
    # No data creation or flush: these immutable tables intentionally reject DELETE.
    def _fixture_teardown(self):
        pass

    def test_additive_guards_exist_and_deny_unowned_mutations(self):
        from mta.runtime.offline_rrr_models import OfflineRrrColourSource, OfflineRrrColourRow
        for model in (OfflineRrrColourSource,OfflineRrrColourRow):
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_trigger WHERE tgrelid=%s::regclass AND NOT tgisinternal",
                    ['mta.'+model._meta.db_table])
                self.assertEqual(cursor.fetchone()[0],3)
            with self.assertRaises(DatabaseError), transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute('DELETE FROM mta.'+model._meta.db_table)
        with self.assertRaisesRegex(DatabaseError,'Explicit owned offline'), transaction.atomic():
            OfflineRrrColourSource.objects.create(run_id='00000000-0000-0000-0000-000000000001',
                input_digest='x',artifact_sha256='x',scenario_sha256='x',recipe_digest='x',
                source_inputs_digest='x',rows_digest='x',row_count=0)
