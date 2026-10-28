"""Complete bags and predecessor ownership for the bounded owned DBM path."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mta.domain import dbm_ingestion as ingestion, dbm_suspensions as suspension
from mta.domain.dbm_suspension_history import gather_suspension_history, CONTRIBUTORS
from mta.row_sequences import RecordRows, history_rows
from mta.serialization import digest

TODAY='2026-06-06'


def values(item):
    if isinstance(item,dict):return {key:values(value) for key,value in item.items()}
    if isinstance(item,(list,RecordRows)):return [values(row) for row in item]
    return item


def state():
    master=dict(SKUCode='S',WhCode='W',Norm=2,MinNorm=3,RLT=2,RCP=2,GCP=2,OCP=4,
                MinOrderCount=0,SKUIntroDate='2026-01-01')
    member=dict(SKUCode='S',WhCode='W',RedEnabled=True,GreenEnabled=True,
                RedResumeDate=None,GreenResumeDate='2026-01-01',SuggestionStartDate=None)
    flag=dict(SKUCode='S',WhCode='W',IsRedEnabled=False,IsGreenEnabled=True)
    result=dict(DBMMaster=[master],SKULocStandardAttributes=[dict(SKUCode='S',WhCode='W',ExtendedOCP=0)],
      LastBatchRunTbl=[dict(LastRunDate=TODAY+'T00:00:00')],DailyConsumption=[],OrderData=[],
      NormChangeLogTbl=[],IntermediateTables=[dict(table='scratch',rows=[dict(v=1)])],
      SuspendStockType=[deepcopy(member)],SuspendConsumptionType=[deepcopy(member)],SuspendOrderType=[deepcopy(member)],
      SuspendStockTypePre=[deepcopy(flag)],SuspendConsumptionTypePre=[deepcopy(flag)],SuspendOrderTypePre=[deepcopy(flag)],
      SuspendAggrCommon=[deepcopy(flag)],SuspendAggrStockType=[deepcopy(flag)],
      SuspendAggrConsumptionType=[deepcopy(flag)],SuspendAggrCommonWithOrderType=[deepcopy(flag)],
      SuspendCustomSKUTbl=[],SuspendHistory=[],sentinel=dict(nested=[dict(v=9)]))
    for table,_,_ in CONTRIBUTORS:result.setdefault(table,[])
    return result


def facts():
    return dict(daily_raw=[dict(SKUCode='S',WhCode='W',Stock=0,Consumption=1,GIT=0,Receipts=0,ReportDate=TODAY)],
      bpr_daily=[dict(SKUCode='S',WhCode='W',BlueZone=2,ReportDate=TODAY)],
      distributor_transactions=[],vendor_transactions=[],exclusions=[],order_raw=[])


class DbmOwnedMemoryTests(unittest.TestCase):
    def test_dispatch_observation_ends_before_yield_and_preserves_native_errors(self):
        from mta.temporal import chain
        from mta.application import stage_observation as observation
        source=state();seen=[]
        def stages(*args,**kwargs):
            seen.append(observation._stages.get()[-1][0])
            yield 'ingestion',source
            raise ValueError('original producer error')
        with patch.object(chain,'selected_stages',side_effect=stages), \
                patch('mta.application.native_output_contracts.producing_native',return_value=True), \
                patch('mta.application.native_output_contracts.validate_dbm_writer'), \
                patch.object(chain,'_observe_dbm') as observe:
            sequence=chain.connected_dbm_stages(TODAY,source,{},None)
            before=observation._stages.get()
            self.assertEqual(next(sequence),('ingestion',source))
            self.assertEqual(observation._stages.get(),before)
            observe.assert_called_once_with(source,'stage_ready','ingestion')
            with self.assertRaisesRegex(ValueError,'original producer error'):next(sequence)
            self.assertEqual(observation._stages.get(),before)
        self.assertEqual(seen,['dbm_dispatch'])

    def test_observer_is_bounded_and_fail_open_without_traversing_factories(self):
        from mta.temporal import chain
        def forbidden():raise AssertionError('observer consumed rows')
        source={'DailyConsumption':RecordRows(12000,forbidden)}
        with patch.object(chain,'summary') as report,patch('pathlib.Path.read_text',side_effect=OSError('unavailable')):
            chain._observe_dbm(source,'stage_ready','ingestion')
            fields=report.call_args.kwargs
            self.assertEqual(fields['populations'],{'DailyConsumption':{'rows':12000,'representation':'RecordRows'}})
        with patch.object(chain,'summary',side_effect=OSError('sink failed')):
            chain._observe_dbm(source,'stage_ready','ingestion')

    def compare(self,fn,source,*args,mutated=()):
        before=values(source)
        expected=fn(*args,deepcopy(source))
        actual=fn(*args,source,_owned=True)
        self.assertEqual(values(actual),values(expected))
        self.assertEqual(values(source),before)
        for table in mutated:
            self.assertIsNot(actual[table],source[table])
            for left,right in zip(actual[table],source[table]):self.assertIsNot(left,right)
        return actual

    def test_selected_suspension_write_sets_preserve_complete_bags_and_rows(self):
        for fn,mutated in (
            (suspension.finalize_stock_suspensions,('SuspendStockType','SuspendAggrCommon','SuspendAggrStockType')),
            (suspension.finalize_consumption_suspensions,('SuspendConsumptionType','SuspendAggrCommon','SuspendAggrConsumptionType')),
            (suspension.finalize_order_suspensions,('SuspendOrderType','SuspendAggrCommonWithOrderType')),
            (suspension.suppress_insufficient_data,('SuspendStockType','SuspendConsumptionType'))):
            for persisted in (False,True):
                source=state()
                if persisted:
                    for table in mutated:source[table]=RecordRows.from_rows(source[table])
                # Default current-row components require mutable rows. Compare
                # equal typed values against their established list control.
                before=values(source);expected=fn(TODAY,deepcopy(before))
                actual=fn(TODAY,source,_owned=True)
                with self.subTest(fn=fn.__name__,persisted=persisted):
                    self.assertEqual(values(actual),expected);self.assertEqual(values(source),before)
                    for table in mutated:
                        if actual[table]:
                            original=values(source[table]);key=next(k for k in actual[table][0] if k.startswith(('Red','IsRed')))
                            actual[table][0][key]='mutation-proof'
                            self.assertEqual(values(source[table]),original)

    def test_preparation_replaces_only_owned_generations_and_keeps_component_default(self):
        source=state();actual=self.compare(suspension.prepare_suspensions,source)
        for table in ('SuspendStockTypePre','SuspendConsumptionTypePre','SuspendOrderTypePre',
                      'SuspendMinNormTbl','SuspendStepOneTbl','SuspendStepOneOrderTypeTbl'):
            if actual[table]:actual[table][0]['SKUCode']='new-only'
        self.assertEqual(source,state())
        default=suspension.prepare_suspensions(source)
        default['sentinel']['nested'][0]['v']=100
        self.assertEqual(source['sentinel']['nested'][0]['v'],9)

    def test_owned_stages_do_not_copy_untouched_graph(self):
        class ReadOnlyDependency(dict):
            def __deepcopy__(self,memo):raise AssertionError('whole-state deepcopy')
        for fn,args in ((suspension.prepare_suspensions,()),(suspension.finalize_stock_suspensions,(TODAY,)),
                        (suspension.finalize_consumption_suspensions,(TODAY,)),
                        (suspension.finalize_order_suspensions,(TODAY,)),(suspension.suppress_insufficient_data,(TODAY,))):
            source=state();source['sentinel']=ReadOnlyDependency(v='borrowed read-only')
            result=fn(*args,source,_owned=True)
            self.assertIs(result['sentinel'],source['sentinel'])

    def test_ingestion_cold_and_persisted_history_full_values_and_mutable_attributes(self):
        for persisted in (False,True):
            source=state();raw=facts()
            raw['daily_raw']*=2
            source['DailyConsumption']=[dict(raw['daily_raw'][0],ReportDate=date(2026,6,5),BlueZone=3)]
            if persisted:
                source['DailyConsumption']=RecordRows.from_rows(source['DailyConsumption'])
                source['SKULocStandardAttributes']=RecordRows.from_rows(source['SKULocStandardAttributes'])
            before=values(source);expected=ingestion.ingest_dbm(TODAY,deepcopy(before),raw)
            actual=ingestion.ingest_dbm(TODAY,source,raw,_owned=True)
            self.assertEqual(values(actual),expected);self.assertEqual(values(source),before)
            self.assertIsInstance(actual['DailyConsumption'],RecordRows)
            self.assertIs(type(actual['DailyConsumption'][0]['ReportDate']),date)
            self.assertEqual(len(actual['DailyConsumption']),3)
            actual['SKULocStandardAttributes'][0]['ExtendedOCP']=123
            self.assertEqual(values(source),before)
        cold=ingestion.ingest_dbm(TODAY,state(),facts(),_owned=True)
        self.assertIsInstance(cold['DailyConsumption'],RecordRows)

    def test_cold_history_option_is_explicit_and_fully_validated(self):
        raw=facts()['daily_raw'];master=state()['DBMMaster'];blue=facts()['bpr_daily']
        with patch('mta.application.native_output_contracts.validate_produced_rows') as validate:
            actual=ingestion.import_daily_observations(TODAY,[],raw,master,blue,[],[],_immutable=True)
            validated=validate.call_args.args[0]
            self.assertIsInstance(validated,RecordRows)
            self.assertEqual(values(validated),values(actual))
        self.assertIsInstance(history_rows(iter(raw),like=[]),list)
        self.assertIsInstance(history_rows(iter(raw),like=[],immutable=True),RecordRows)

    def test_input_ambiguity_and_date_failure_order_match_component_path(self):
        source=state();raw=facts();raw['bpr_daily'].append(dict(raw['bpr_daily'][0],BlueZone=99))
        for owned in (False,True):
            with self.assertRaisesRegex(ValueError,'conflicting BPR BlueZone'):
                ingestion.ingest_dbm(TODAY,source,raw,_owned=owned)
        source=state();source['LastBatchRunTbl'][0]['LastRunDate']=TODAY+'T01:00:00'
        for fn in (suspension.finalize_stock_suspensions,suspension.finalize_consumption_suspensions,
                   suspension.suppress_insufficient_data):
            errors=[]
            for owned in (False,True):
                try:fn(TODAY,source,_owned=owned)
                except Exception as e:errors.append((type(e),str(e)))
            self.assertEqual(len(errors),2);self.assertEqual(errors[0],errors[1])

    def test_suspension_history_duplicate_join_horizon_and_contributor_error_order(self):
        source=state();source['SuspendStockType']*=2;source['SuspendConsumptionType']*=2
        historical=dict(SKUCode='old',WhCode='W',RedEnabledStockType=True,GreenEnabledStockType=False,
          RedEnabledConsumptionType=False,GreenEnabledConsumptionType=True,
          RedReasonStockType=0,GreenReasonStockType=0,RedReasonConsumptionType=0,GreenReasonConsumptionType=0)
        source['SuspendHistory']=[dict(historical,ReportDate=d) for d in ('2026-03-07','2026-03-09',TODAY)]
        source['SuspendCustomSKUTbl']=[dict(SKUCode='S',WhCode='W',IsRedEnabled=False,IsGreenEnabled=True)]*2
        before=values(source);expected=gather_suspension_history(TODAY,deepcopy(source))
        actual=gather_suspension_history(TODAY,source,_owned=True)
        self.assertEqual(values(actual),expected);self.assertEqual(values(source),before)
        self.assertIsInstance(actual['SuspendHistory'],RecordRows)
        self.assertEqual(len(actual['SuspendHistory']),5)
        self.assertEqual(actual['SuspendHistory'][-1]['RedReasonStockType'],1)
        source['SuspendCustomSKUTbl'].append(dict(source['SuspendCustomSKUTbl'][0],IsRedEnabled=True))
        source['SuspendWhitesTbl']=[dict(SKUCode='S',WhCode='W',IsRedEnabled=v,IsGreenEnabled=True) for v in (False,True)]
        for owned in (False,True):
            with self.assertRaisesRegex(ValueError,'contributor SuspendCustomSKUTbl'):
                gather_suspension_history(TODAY,source,_owned=owned)

    def test_native_validation_checks_all_cold_rows_and_keeps_error_text(self):
        from mta.application.native_output_contracts import native_assignments
        source=facts();raw=source['daily_raw']
        with native_assignments():
            actual=ingestion.import_daily_observations(TODAY,[],raw,state()['DBMMaster'],source['bpr_daily'],[],[],_immutable=True)
            self.assertEqual(len(actual),1)
            errors=[]
            for immutable in (False,True):
                bad=[dict(raw[0]),dict(raw[0],Stock='invalid')]
                try:ingestion.import_daily_observations(TODAY,[],bad,state()['DBMMaster'],source['bpr_daily'],[],[],_immutable=immutable)
                except Exception as error:errors.append((type(error),str(error)))
            self.assertEqual(len(errors),2);self.assertEqual(errors[0],errors[1])

    def test_large_cold_history_seals_without_a_complete_list_builder(self):
        count=12000;rows=RecordRows(count,lambda:(dict(SKUCode=str(i),WhCode='W',Stock=i%2,
            Consumption=1,GIT=0,Receipts=0,ReportDate=TODAY) for i in range(count)))
        masters=RecordRows(count,lambda:(dict(SKUCode=str(i),WhCode='W') for i in range(count)))
        expected=ingestion.import_daily_observations(TODAY,[],rows,masters,[],[],[])
        original=RecordRows.from_rows
        def seal(source):
            self.assertNotIsInstance(source,list)
            return original(source)
        with patch.object(RecordRows,'from_rows',side_effect=seal):
            result=ingestion.import_daily_observations(TODAY,[],rows,masters,[],[],[],_immutable=True)
        self.assertIsInstance(result,RecordRows);self.assertEqual(len(result),count)
        self.assertEqual(list(result),expected)
        self.assertEqual(result[0]['SKUCode'],'0');self.assertEqual(result[-1]['SKUCode'],str(count-1))
        self.assertEqual(sum(r['Consumption'] for r in result),count)
        self.assertEqual(sum(r['Consumption'] for r in result),count)

    def test_large_cold_suspension_history_streams_each_contributor_generation(self):
        count=12000;source=state()
        member=source['SuspendStockType'][0]
        for name in ('SuspendStockType','SuspendConsumptionType'):
            source[name]=RecordRows(count,lambda:(dict(member,SKUCode=str(i)) for i in range(count)))
        source['SuspendCustomSKUTbl']=[dict(SKUCode=str(i),WhCode='W',IsRedEnabled=False,IsGreenEnabled=True)
            for i in (0,count-1)]
        before=digest(source)
        expected=gather_suspension_history(TODAY,source)['SuspendHistory']
        original=RecordRows.from_rows
        def seal(rows):
            self.assertNotIsInstance(rows,list)
            return original(rows)
        with patch.object(RecordRows,'from_rows',side_effect=seal):
            actual=gather_suspension_history(TODAY,source,_owned=True)['SuspendHistory']
        self.assertIsInstance(actual,RecordRows)
        self.assertEqual(list(actual),expected);self.assertEqual(digest(source),before)
        self.assertEqual(len(actual),count)
        self.assertEqual([actual[i]['RedReasonStockType'] for i in (0,1,count-1)],[1,0,1])

    def test_assembly_does_not_copy_discarded_prior_generations_and_preserves_order(self):
        from tests.test_h3_daily_integration import frame
        from mta.temporal import chain
        class Discarded(list):
            def __deepcopy__(self,memo):raise AssertionError('discarded generation copied')
        f=frame();prior=f['opening']['state'];replaced={*chain.SHARED_CONTROLS.values(),'SKULocStandardAttributes',
          'SKUDescriptionTbl','SiteDescriptionTbl','SkuAttributeData','LocationAttributeData','SkuLocAttributeData','LastBatchRunTbl'}
        for name in replaced:prior['dbm'][name]=Discarded([dict(discarded=name)])
        context=SimpleNamespace(prior=prior,day={n:[] for n in ('order_raw','exclusions','distributor_transactions','vendor_transactions')},
          profile=f['profile'],report_exceptions={},today=TODAY,now=TODAY+'T00:00:00',finalization=True)
        phase=SimpleNamespace(context=context,importer=prior['importer'],control_final=prior['controls'],completed_boundaries=[],
          delivery=None,daily_final={'DailyDataRaw':[]},standard_attributes=[],late={'BPRDailyConsumption':[]})
        class Inspected(Exception):pass
        def inspect(today,current,*args):
            self.assertEqual(list(current)[:len(prior['dbm'])],list(prior['dbm']))
            self.assertFalse(any(isinstance(current[n],Discarded) for n in replaced))
            self.assertIsNot(current['DBMMaster'],prior['dbm']['DBMMaster'])
            raise Inspected
        with patch.object(chain,'connected_dbm_stages',side_effect=inspect):
            with self.assertRaises(Inspected):chain.produce_dbm(phase)
        self.assertTrue(all(isinstance(prior['dbm'][n],Discarded) for n in replaced))
