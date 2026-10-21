"""BTR values, persisted-row ownership and actual producer lifetime boundaries.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date, timedelta
import unittest
import weakref
from unittest.mock import patch

from mta.domain import btr_finalization as btr
from mta.row_sequences import RecordRows
from mta.serialization import storage, digest


class BtrMemoryLifetimeTests(unittest.TestCase):
    def test_pivot_keeps_all_ordered_columns_nulls_max_and_duplicate_rows(self):
        today=date(2026,4,8)
        rows=[dict(SKUCode='SKU',WHCode='WH',ReportDate='2026-04-08',TechPen=value)
              for value in (None,'Black','Red')]
        rows.append(dict(SKUCode='SKU',WHCode='WH',ReportDate='2026-04-06',TechPen='Green'))
        expected={name:None for name in btr.DAYS}
        expected.update(D88='Green',D90='Red')
        for source in (rows,RecordRows.from_rows(rows)):
            actual=btr._pivot(source,today,'TechPen')
            self.assertEqual([(tuple(key),values) for key,values in actual.items()],[(('SKU','WH'),expected)])
            self.assertEqual(tuple(next(iter(actual.values()))),btr.DAYS)

    def test_colour_age_retains_duplicate_counts_gaps_and_independent_input(self):
        today=date(2026,4,8)
        history=[]
        for offset,colour,multiplicity in ((0,'Black',2),(1,'Red',1),(3,'Black',1)):
            history.extend(dict(SKUCode='SKU',WHCode='WH',
                ReportDate=(today-timedelta(days=offset)).isoformat(),
                TechColor=colour,EcoColor=None,DispatchColor=colour,PhysicalInventoryColor=colour)
                for _ in range(multiplicity))
        row=dict(SKUCode='SKU',WhCode='WH',Age=37,
            **{name:None for name in btr.DAYS},**{colour+'Count':99 for colour in btr.COLOURS})
        state=dict(BPR=history,BufferTrendDispatch=[deepcopy(row)],BufferTrendPhysicalInv=[deepcopy(row)])
        before=deepcopy(state)
        for source in (state,dict(state,BPR=RecordRows.from_rows(history))):
            actual=btr._colour_age(today,source,True,1,_owned=True,_operational=True)
            for table in ('BufferTrendDispatch','BufferTrendPhysicalInv'):
                self.assertEqual(actual[table][0]['Age'],1)
                self.assertEqual([actual[table][0][colour+'Count'] for colour in btr.COLOURS],
                                 [0,0,0,0,1,3])
                actual[table][0]['Age']=100
                self.assertEqual(source[table][0]['Age'],37)
        self.assertEqual(state,before)

    def test_persisted_nonempty_history_preserves_operational_and_report_values(self):
        from tests.test_operational_btr_boundary import case
        today,prior,facts,settings,owner=case()
        settings=dict(settings,GenerateColorAgeingReport=1,CaptureDispatchExecutionEfficiency=0)
        prior['BPR']=[]
        for offset in (1,2,4,35,89,95):
            for row in facts['vf_RationedReqReport']:
                record={field:row[field] for field in btr.BPR_SOURCE_FIELDS}
                record.update(WHCode=row['WhCode'],ReportDate=(date.fromisoformat(today)-timedelta(days=offset)).isoformat())
                record.pop('WhCode');prior['BPR'].append(record)
        expected=list(btr.btr_stages(today,prior,facts,settings,importer_vf_settings=owner,
                                    _owned=True,_reporting=False))[-1][1]
        source={name:RecordRows.from_rows(rows) for name,rows in prior.items()}
        inputs={name:RecordRows.from_rows(rows) for name,rows in facts.items()}
        before=digest(dict(prior=source,facts=inputs))
        actual=list(btr.btr_stages(today,source,inputs,settings,importer_vf_settings=owner,
                                  _owned=True,_reporting=False))[-1][1]
        self.assertEqual(storage(actual),storage(expected))
        self.assertEqual(storage(btr.reporting_btr(today,actual,inputs,settings,importer_vf_settings=owner)),
                         storage(btr.reporting_btr(today,expected,facts,settings,importer_vf_settings=owner)))
        self.assertEqual(digest(dict(prior=source,facts=inputs)),before)

    def test_real_daily_path_releases_dbm_stage_owners_before_btr_and_keeps_final_independence(self):
        from tests.test_h3_daily_integration import frame,coupled
        from mta.temporal import chain
        class Generation(dict):pass
        references=[]; observed=[]
        original_dbm,original_btr=chain.connected_dbm_stages,chain.connected_btr_stages
        def dbm(*args,**kwargs):
            for name,state in original_dbm(*args,**kwargs):
                current=Generation(state);references.append(weakref.ref(current))
                yield name,current
        def trends(*args,**kwargs):
            # This is the real next producer boundary, not a source-code check
            # for a particular del statement. Required report rows survive in
            # their independently owned images, not the DBM working wrappers.
            self.assertTrue(references)
            self.assertFalse(any(reference() is not None for reference in references))
            observed.append(True)
            yield from original_btr(*args,**kwargs)
        f=frame();before=digest(f)
        with patch.object(chain,'connected_dbm_stages',side_effect=dbm), \
                patch.object(chain,'connected_btr_stages',side_effect=trends):
            result,_=coupled(f['profile'],f['opening']['state'],'2037-04-09','2037-04-10')
        self.assertEqual(observed,[True]);self.assertEqual(digest(f),before)
        closing=result['ClosingState'][0]
        for closing_rows,final_rows in (
            (closing['dbm']['SKULocStandardAttributes'],result['DBMFinal'][0]['SKULocStandardAttributes']),
            (closing['btr']['SKULocStandardAttributes'],result['BTRFinal'][0]['SKULocStandardAttributes'])):
            self.assertTrue(closing_rows);self.assertEqual(closing_rows,final_rows)
            original=deepcopy(final_rows)
            closing_rows[0]['Category']='test-only-mutation'
            self.assertEqual(final_rows,original)
        self.assertTrue(result['Reports'])

    def test_complete_candidate_uses_unchanged_typed_manifest_and_reader_contract(self):
        from types import SimpleNamespace
        from tests.test_h3_daily_integration import frame,coupled
        from mta.runtime import relational_state as relational
        f=frame()
        output,_=coupled(f['profile'],f['opening']['state'],'2037-04-09','2037-04-10')
        images={};exports={};written=[]
        before=digest(output)
        image_writer,export_writer=relational.save_image,relational.save_export
        def save_image(run,path,binding,rows):
            # Only the SQL transport is replaced. The real manifest traversal,
            # family binding, canonical representation and complete readback
            # remain exercised; this is not a PostgreSQL transaction proof.
            images[path]=storage(deepcopy(rows))
            return image_writer(run,path,binding,rows)
        def save_export(run,path,rows):
            exports[path]=storage(deepcopy(rows));return export_writer(run,path,rows)
        def transport(sql,records):
            # Exhaust the real typed conversion generator, retaining ordinals
            # and values, while making no connection or database write.
            written.append((sql,list(records)))
        run=SimpleNamespace(pk='1f3a5a5f-10ec-4f2d-a64d-12627d7c5310')
        with patch.object(relational,'connection',SimpleNamespace(vendor='sqlite')), \
                patch.object(relational,'bulk',side_effect=transport), \
                patch.object(relational,'save_image',side_effect=save_image), \
                patch.object(relational,'save_export',side_effect=save_export), \
                patch.object(relational,'load_image',side_effect=lambda run,item:deepcopy(images[item['image']])), \
                patch.object(relational,'load_export',side_effect=lambda run,item:deepcopy(exports[item['image']])):
            run.production_manifest=relational.save_daily(run,output)
            actual=relational.read_daily(run)
        self.assertEqual(storage(actual),storage(relational.production_projection(output)))
        self.assertEqual(digest(output),before)
        self.assertTrue(images)
        self.assertTrue(written)
        self.assertTrue(actual['ClosingState'][0]['btr']['BPR'])
        self.assertTrue(actual['BTRFinal'][0]['SKULocStandardAttributes'])


if __name__=='__main__':unittest.main()
