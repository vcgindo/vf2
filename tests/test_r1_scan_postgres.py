"""Real typed-reader threshold and R1 joins in the owned small proof database.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import os
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('VF_R1_SCAN_PROOF')=='1','Explicit owned PostgreSQL proof required')
class R1ScanPostgresTests(unittest.TestCase):
    def test_real_10001_row_typed_spool_and_first_match_join_rollback(self):
        from django.db import connection, transaction
        from mta.runtime.models import CalculationRun
        from mta.runtime import relational_state as typed
        from mta.row_sequences import RecordRows
        from mta.planning import projections
        self.assertEqual(connection.settings_dict['NAME'],'vf_daily_optimization_20261021')
        self.assertTrue(os.environ.get('VF_WORK_ROOT'))
        before=CalculationRun.objects.count()
        with transaction.atomic():
            run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2037-04-10',
                execution_revision='r1-scan-typed-component-only',input_digest='8'*64,
                input_payload={},status='RUNNING')
            rows=[dict(SKUCode=str(i),WHCode='C',Stock=i%11-3,Consumption=0,
                GIT=i%3,Receipts=0,PSO=0,BlueZone=None,ReportDate='2037-04-10') for i in range(10001)]
            image=typed.save_image(run,'r1-scan/component-daily','r1-scan/component-daily',
                rows,table='BPR/DailyConsumption')
            loaded=typed.load_image(run,image)
            self.assertIsInstance(loaded,RecordRows)
            self.assertTrue(hasattr(loaded,'_data'))  # actual file spool, not a marker wrapper
            self.assertEqual(list(loaded),rows)
            positions=RecordRows.from_rows(dict(sku_code=r['SKUCode'],location_code=r['WHCode'],
                stock_quantity=r['Stock'],goods_in_transit_quantity=r['GIT']) for r in loaded)
            prepared=SimpleNamespace(track_a={'foundation':{'hierarchy':[],
                'inventory_positions':positions}},phase_out_membership=())
            selected=(10000,0,5000)
            requirements=[dict(sku_code=str(i),location_code='C',effective_norm={'value':'10'},
                requirement=dict(pso='0',pso_threshold='100',due_spike='0',routed_due_spike='0')) for i in selected]
            with patch.object(projections,'calculate_requirement_bands',side_effect=lambda values,**kw:values):
                actual=projections._requirement_band_rows(prepared,{'policies':[]},requirements,[],[])
            self.assertEqual([(r.sku_code,r.stock,r.goods_in_transit) for r in actual],
                [(str(i),Decimal(i%11-3),Decimal(i%3)) for i in selected])
            self.assertEqual(list(loaded),rows)
            transaction.set_rollback(True)
        self.assertEqual(CalculationRun.objects.count(),before)
        self.assertFalse(CalculationRun.objects.filter(execution_revision='r1-scan-typed-component-only').exists())
        print('R1_TYPED_10001_POSTGRES_PASS actual-file-spool signed-zero-NULL ordered-values original-unchanged rollback')


if __name__ == '__main__':
    unittest.main()
