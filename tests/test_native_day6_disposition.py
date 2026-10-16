"""Day-six scope and disclosure, while day-five tests retain their exact contract."""
from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import unittest
import zipfile

from tests.test_native_report_disposition import state, batch, RUN, OUTPUT
from mta.application import native_report_disposition as d
from mta.application.norm0_reports import resultsets, export_files
from mta.domain.dbm_selected_chain import selected_norm012_stages
from mta.domain.dbm_norm012 import AmbiguousReport, NORM0_EXPORT_STAGES
from mta.temporal.chain import retain_dbm_stages
from mta.evidence import evidence_mode


def day6state():
    value = state()
    value['LastBatchRunTbl'][0]['LastRunDate'] = '2026-10-18T00:00:00'
    value['DailyConsumption'].append(dict(value['DailyConsumption'][-1], ReportDate='2026-10-18'))
    return value


def reports(source=None, limited=True, configuration=None):
    with evidence_mode('production'):
        stages = retain_dbm_stages(selected_norm012_stages('2026-10-18', source or day6state(),
            configuration or batch(), {'native_report_disposition': d.binding(d.DAY6_ID)} if limited else None), [])
    return [dict(stage=n,tables=v) for n,v in stages if n in NORM0_EXPORT_STAGES.values()]


class Day6DispositionTests(unittest.TestCase):
    def test_typed_six_and_disclosure_preserve_other_horizons(self):
        source=day6state(); before=deepcopy(source); actual=reports(source)
        self.assertEqual(source,before)
        row=actual[0]['tables']['Norm0Norm1Norm2Report'][0]
        self.assertEqual(row['Count'],6); self.assertEqual(row['TotalSale'],6)
        self.assertIs(type(row['Count']),int); self.assertIsNone(row['Occurances'])
        self.assertEqual(actual[1:],reports(limited=False,configuration=batch((60,90))))
        receipt=resultsets(reports=actual,batch=batch(),run_id=RUN,output_digest=OUTPUT,
            lineage=[{'native_report_disposition':d.binding(d.DAY6_ID)}])
        self.assertEqual(receipt['qualification'],'COMPLETE_WITH_LEGACY_FLAWS')
        with TemporaryDirectory() as root:
            exported=export_files(root=root,receipt=receipt)
            with zipfile.ZipFile(Path(root)/exported['artifacts'][0]['archive']['relative_path']) as z:
                self.assertIn(d.DISPLAY.encode(),z.read('Norm_0_Report_30Days.csv'))
                meta=json.loads(z.read('Norm_0_Report_30Days.metadata.json'))
                self.assertEqual(meta['native_report_disposition'],d.binding(d.DAY6_ID))

    def test_no_exception_or_another_group_still_fails(self):
        with self.assertRaises(AmbiguousReport): reports(limited=False)
        s=day6state();s['DBMMaster'].append(dict(s['DBMMaster'][0],SKUCode='OTHER'))
        s['SKUDescriptionTbl'].append(dict(s['SKUDescriptionTbl'][0],SKUCode='OTHER'))
        s['DailyConsumption'] += [dict(r,SKUCode='OTHER') for r in s['DailyConsumption']]
        with self.assertRaises(AmbiguousReport): reports(s)

    def test_row_type_order_count_date_and_numeric_drift_denied(self):
        for mutation in ('quantity','bool','date','duplicate','missing','order'):
            s=day6state();rows=s['DailyConsumption']
            if mutation=='quantity':rows[0]['Consumption']=2
            if mutation=='bool':rows[0]['Consumption']=True
            if mutation=='date':rows[0]['ReportDate']='2026-10-12'
            if mutation=='duplicate':rows.append(deepcopy(rows[0]))
            if mutation=='missing':rows.pop()
            if mutation=='order':rows.reverse()
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): reports(s)
        for field in ('Count','TotalSale'):
            actual=reports();actual[0]['tables']['Norm0Norm1Norm2Report'][0][field]=5
            with self.assertRaises(ValueError):
                resultsets(reports=actual,batch=batch(),run_id=RUN,output_digest=OUTPUT,
                    lineage=[{'native_report_disposition':d.binding(d.DAY6_ID)}])

    def test_binding_scope_and_cross_case_replay_denied(self):
        for field,value in [('business_date',d.DAY),('input_digest',d.INPUT),('origin_run_id',d.ORIGIN),
                ('predecessor_id',d.PARENT),('horizon',60),('SKUCode','OTHER'),('norm',False)]:
            b=d.binding(d.DAY6_ID);b['policy'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):d.require_binding(b)
        for day,norm,horizon in [(d.DAY,0,30),('2026-10-18',1,30),('2026-10-18',0,60)]:
            with self.assertRaises(ValueError):d.report_group(day,day6state(),d.binding(d.DAY6_ID),norm=norm,horizon=horizon)
        p=d.DAY6_POLICY
        run=SimpleNamespace(input_digest=p['input_digest'],predecessor_id=p['predecessor_id'],
            business_date=date.fromisoformat(p['business_date']),execution_revision=d.DAY6_RETRY,
            status='SUCCEEDED',production_manifest={})
        lineage=[{'native_report_disposition':d.binding(d.DAY6_ID)}]
        d.verify_replay(run,lineage,d.DAY6_ID)
        with self.assertRaises(ValueError):d.verify_replay(run,lineage,d.ID)
        with self.assertRaises(ValueError):d.verify_replay(run,lineage,None)


if __name__=='__main__':unittest.main()
