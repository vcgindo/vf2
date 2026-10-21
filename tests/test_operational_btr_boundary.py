"""Full BTR closure versus rebuilding only derived presentation populations.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','section11-unit-only')
import django
django.setup()
from copy import deepcopy
from datetime import date,timedelta
from pathlib import Path
import json,unittest,zipfile
from mta.domain import btr_finalization as btr
from mta.mdm.initialization_contract import decode_value
from mta.serialization import digest,storage
from mta.row_sequences import RecordRows


def case():
    with zipfile.ZipFile(Path(__file__).resolve().parents[1]/'examples/starter-data/vectorflow-starter-inputs-v1.zip') as archive:
        value=json.loads(archive.read('initialization.json'))
    _,frame,_=decode_value(value,expected_configuration=digest(value['configuration']),expected_recipe=digest(value['recipe']))
    state=frame['opening']['state']
    today=(date.fromisoformat(frame['opening']['opening_date'])+timedelta(days=1)).isoformat()
    facts={**state['consumer_context'],**state['importer'],**state['dbm']}
    for table in btr.FACT_TABLES:facts.setdefault(table,[])
    reports=[]
    for master in state['importer']['MasterData']:
        row=dict.fromkeys(btr.BPR_SOURCE_FIELDS)
        row.update(SKUCode=master['SKUCode'],WhCode=master['WhCode'],ParentWhCode=master['ParentWhCode'],
            Norm=10,VirtualNorm=10,Stock=0,GIT=0,RationedReq=1,TechPen='100.00',TechColor='Black',EcoPen='100.00',EcoColor='Black',
            DispatchPen='100.00',DispatchColor='Black',PhysicalInventoryPen='100.00',PhysicalInventoryColor='Black')
        reports.append(row)
    facts.update(vf_RationedReqReport=reports,BPR_Table=deepcopy(reports),MasterData=state['importer']['MasterData'])
    settings=frame['profile']['delivery']['btr_settings']
    owner=frame['profile']['delivery'].get('btr_history',{}).get('importer_vf_settings')
    return today,state['btr'],facts,settings,owner


class OperationalBtrBoundaryTests(unittest.TestCase):
    def test_complete_operational_values_and_report_rebuild_match_full_boundary(self):
        today,prior,facts,settings,owner=case()
        before=digest(storage(dict(prior=prior,facts=facts)))
        full=list(btr.btr_stages(today,prior,facts,settings,importer_vf_settings=owner,_owned=True))[-1][1]
        operational=list(btr.btr_stages(today,prior,facts,settings,importer_vf_settings=owner,_owned=True,_reporting=False))[-1][1]
        self.assertFalse(btr.DERIVED_TABLES.intersection(operational))
        self.assertEqual(storage(operational),storage({k:v for k,v in full.items() if k not in btr.DERIVED_TABLES}))
        rebuilt=btr.reporting_btr(today,operational,facts,settings,importer_vf_settings=owner)
        self.assertEqual(storage(rebuilt),storage({k:full[k] for k in btr.DERIVED_TABLES}))
        self.assertEqual(before,digest(storage(dict(prior=prior,facts=facts))))
        self.assertTrue(rebuilt['BTRSnapshotForUI'])
        self.assertIn('BPPTech',rebuilt['BTRSnapshotForUI'][0])

    def test_report_rebuild_reads_actual_spooled_source_generations(self):
        today,prior,facts,settings,owner=case()
        operational=list(btr.btr_stages(today,prior,facts,settings,importer_vf_settings=owner,_owned=True,_reporting=False))[-1][1]
        expected=btr.reporting_btr(today,operational,facts,settings,importer_vf_settings=owner)
        spooled={name:RecordRows.from_rows(rows) for name,rows in operational.items()}
        source={name:RecordRows.from_rows(rows) for name,rows in facts.items()}
        self.assertEqual(storage(btr.reporting_btr(today,spooled,source,settings,importer_vf_settings=owner)),storage(expected))

    def test_ninety_day_scalar_closure_and_all_rebuilt_matrices(self):
        for enabled in (0,1):
            with self.subTest(generate_age=enabled):
                today,prior,facts,settings,owner=case()
                settings=dict(settings,GenerateColorAgeingReport=enabled,CaptureDispatchExecutionEfficiency=0)
                dates=[(date.fromisoformat(today)-timedelta(days=i)).isoformat() for i in range(1,96)]
                prior['BPR']=[dict(row,WHCode=row['WhCode'],ReportDate=stamp)
                    for row in facts['vf_RationedReqReport'] for stamp in dates]
                for row in prior['BPR']:row.pop('WhCode')
                facts['ExpediteDispatches']=[dict(SKUCode=row['SKUCode'],WhCode=row['WhCode'],
                    BRAge=None,BRAgeRedCount=None,BRAgeBlackCount=None) for row in facts['vf_RationedReqReport']]
                full=list(btr.btr_stages(today,prior,facts,settings,importer_vf_settings=owner,_owned=True))[-1][1]
                operational=list(btr.btr_stages(today,prior,facts,settings,importer_vf_settings=owner,_owned=True,_reporting=False))[-1][1]
                self.assertEqual(storage(operational),storage({k:v for k,v in full.items() if k not in btr.DERIVED_TABLES}))
                rebuilt=btr.reporting_btr(today,operational,facts,settings,importer_vf_settings=owner)
                self.assertEqual(storage(rebuilt),storage({k:full[k] for k in btr.DERIVED_TABLES}))
                # Canonical 90-date pivot and contiguous black-tail age, not
                # merely candidate-versus-candidate equality.
                self.assertTrue(all(row['BRAge']==90 and row['BRAgeBlackCount']==90
                    for row in operational['ExpediteDispatches']))
                self.assertEqual(len(rebuilt['BufferTrendPhysicalInv'][0]),110)
                self.assertEqual(rebuilt['BufferTrendPhysicalInv'][0]['D1'],'Black')
                self.assertEqual(rebuilt['BufferTrendPhysicalInv'][0]['D90'],'Black')

    def test_ambiguous_colour_history_still_fails_before_operational_commit(self):
        today,prior,facts,settings,owner=case()
        row=facts['vf_RationedReqReport'][0]
        stamp=(date.fromisoformat(today)-timedelta(days=1)).isoformat()
        source=dict(row,WHCode=row['WhCode'],ReportDate=stamp);source.pop('WhCode')
        prior['BPR']=[source,dict(source,DispatchColor='Red')]
        settings=dict(settings,GenerateColorAgeingReport=1,CaptureDispatchExecutionEfficiency=0)
        before=digest(storage(dict(prior=prior,facts=facts)))
        for reporting in (False,True):
            with self.assertRaisesRegex(ValueError,'conflicting BPR colours'):
                list(btr.btr_stages(today,prior,facts,settings,importer_vf_settings=owner,_owned=True,_reporting=reporting))
        self.assertEqual(before,digest(storage(dict(prior=prior,facts=facts))))


if __name__=='__main__':unittest.main()
