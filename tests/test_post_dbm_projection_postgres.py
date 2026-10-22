"""Read-only follow-up for the post-commit master adapter; no new day."""
import os,unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('VF_POST_DBM_PERSISTENCE_PROOF')=='1','Explicit owned post-DBM SQL proof required')
class PostDbmProjectionPostgres(unittest.TestCase):
    def test_actual_typed_closing_matches_all_current_master_partitions(self):
        from django.db import connection,transaction
        from mta.runtime.models import CalculationRun,ProductionInitialization
        from mta.runtime import relational_state as typed
        from mta.mdm import daily_current,location_projection
        from mta.row_sequences import RecordRows
        from mta.serialization import digest
        self.assertEqual(connection.settings_dict['NAME'],'vf_btr_terminal_admission_20261022')
        original_load=typed.load_image
        reads=[]
        def spool(run,item):
            value=original_load(run,item)
            reads.append(item['image'])
            return value if isinstance(value,RecordRows) else RecordRows.from_rows(value)
        with transaction.atomic(),connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION READ ONLY')
            owner=ProductionInitialization.objects.select_related('source').get()
            run=CalculationRun.objects.get(status='SUCCEEDED')
            self.assertEqual(digest(run.production_manifest),run.production_digest)
            typed_output=typed.read_daily(run,include_reports=False)
            expected=daily_current.identity(typed_output['ClosingState'][0],version=location_projection.VERSION)
            with patch.object(typed,'load_image',side_effect=spool):
                spooled=typed.read_daily(run,include_reports=False)['ClosingState'][0]
            before=digest(spooled)
            daily_current.verify_current(owner.source,spooled,version=location_projection.VERSION)
            self.assertEqual(daily_current.identity(spooled,version=location_projection.VERSION),expected)
            self.assertEqual(digest(spooled),before)
            self.assertTrue(all(isinstance(spooled['importer'][name],RecordRows) for name in
                ('MasterData','SkuLocAttributeData','SkuAttributeData','LocationAttributeData')))
            self.assertGreater(len(reads),0)
        print('POST_DBM_CURRENT_PROJECTION_SQL_PASS all current partitions/full values/actual typed spools read-only/no new day')
