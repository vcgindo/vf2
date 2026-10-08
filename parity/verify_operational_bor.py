"""Bounded rollback-only native BOR collection/export/history proof.

Strict typed sequences are required. Unordered-table bags are diagnostic only;
the separate Pick export qualification is not transferred to these reports.
"""
import argparse
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.application import operational_bor as bor
from mta.domain.complete_daily_scalars import ascii_equal
from mta.serialization import storage
from parity.adapters.legacy.complete_daily_sql import namespace, preflight_scripts
from parity.verify_complete_daily_pick_files import prepare, preflight_fixtures, restore_resultset
from parity.verify_complete_daily_completion import execute_native
from parity.verify_complete_daily_producers import OWNER, SOURCE, FixtureSQL, compare_rows, native_context
from tests.test_operational_bor import requirement, rationed, bor_row, rrr_row

EVIDENCE = Path('D:/freshvcf-build/evidence/cohort2-20261008-001')
TODAY = date(2026, 6, 6)
CODE = ('mta/application/operational_bor.py', 'parity/verify_operational_bor.py',
        'tests/test_operational_bor.py', 'parity/verify_complete_daily_producers.py',
        'parity/verify_complete_daily_completion.py', 'parity/verify_complete_daily_pick_files.py',
        'parity/adapters/legacy/complete_daily_sql.py', 'parity/legacy_isolation.py')


class BorFixtureSQL(FixtureSQL):
    def fill(self, column):
        value, reason = super().fill(column)
        if isinstance(value, Decimal):
            value = value.quantize(Decimal(1).scaleb(-column['scale']))
        return value, reason


def pin(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cases():
    for name, moq, duplicate, empty, descriptions in (
        ('positive', 0, False, False, True),
        ('moq-duplicate-description', 20, True, False, True),
        ('missing-description', 0, False, False, False),
        ('explicit-empty', 0, False, True, False),
    ):
        current = [] if empty else [requirement()]
        rr = [] if empty else [rationed()] * (2 if duplicate else 1)
        source = dict(bpr_master=[] if empty else [dict(SKUCode='S', WHCode='W', ParentWhCode='P')],
            sob_data=[] if empty else [dict(SKUCode='S',WHCode='W',SupplierCode='P',SOB=100.0)],
            moq_data=[] if empty else [dict(SKUCode='S',WHCode='W',SupplierCode='P',MOQ=moq)],
            requirements=current, rationed_report=rr, bpr_table=[])
        report = dict(color_sequence=[dict(Color='Black',SequenceNo=1)],
            sku_descriptions=([dict(SKUCode='S',SKUDescription='Some, SKU')] * (2 if duplicate else 1))
                if descriptions else [],
            site_descriptions=[dict(WHCode='W',WHDescription='Some, Site'),
                               dict(WHCode='P',WHDescription='Parent')] if descriptions else [],
            requirement_rows=[] if empty else [dict(SKUCode='S',WhCode='W',AdvAllocDone=5)],
            is_mto_environment=0)
        history_dates = [TODAY, TODAY-timedelta(days=90), TODAY-timedelta(days=89)]
        history = [{**bor_row(), 'ReportDate':day.isoformat()} for day in history_dates]
        rrr_history = [{**rrr_row(), 'ReportDate':day.isoformat()} for day in history_dates]
        declared = {('BPR',table):deepcopy(rows) for table,rows in (
            ('BPRMaster',source['bpr_master']), ('SOBData',source['sob_data']), ('MOQData',source['moq_data']),
            ('RequirementInColorBand',current), ('vf_RationedReqReport',rr), ('BPR_Table',[]),
            ('BORWithOrderAllocation',[]), ('BOR_OrderAllocationHistory',history),
            ('RRR_OrderAllocation',[]), ('RRR_OrderAllocationHistory',rrr_history),
            ('LastBatchRunTbl',[dict(LastRunDate=datetime.combine(TODAY,datetime.min.time()))]),
            ('ColorSequence',report['color_sequence']), ('SKUDescriptionTbl',report['sku_descriptions']),
            ('SiteDescriptionTbl',report['site_descriptions']), ('vf_ReqCalculation',report['requirement_rows']))}
        declared[('Importer','ScriptExecutedFlag')] = [dict(ScriptName='CollectBOR_OrderAllocationData.sql',
            ModuleName='BPR',IsScriptExecuted=False,IsScriptCritical=True)]
        yield name, source, report, history, rrr_history, declared


def strict_rows(sql, key, expected):
    result=compare_rows(sql.rows(*key),expected,sql.schema(*key))
    result['bag_status']=result['status']
    result['policy']='exact native typed row sequence; bag differences diagnostic only'
    result['status']='PASS' if result['native_sequence']==result['modern_sequence'] else 'FAIL'
    return result


def run(owner, output, selected=None):
    output=Path(output).resolve()
    if owner != OWNER or not output.is_relative_to(EVIDENCE.resolve()) or output.suffix!='.json' or output.exists():
        raise ValueError('Exact owned Cohort2 evidence path and SQL namespace required')
    from parity import legacy_isolation as isolation
    _, setup = prepare(owner,isolation)
    os.environ['VFTEST_PROFILE']='fresh'
    mapping=namespace(owner)
    variables=dict(IntermediateDatabase=mapping['VFTEST_Intermediate'],IsMTOEnvironment=0,
        BOROAHistoryHorizon=90,RRROAHistoryHorizon=90,
        ScriptExecutionFlagQuery='UPDATE '+mapping['VFTEST_Importer']+
            '.dbo.ScriptExecutedFlag SET IsScriptExecuted=1 WHERE ScriptName=')
    scripts=dict(zip(bor.SOURCES,preflight_scripts([
        dict(source_path=(SOURCE/path).as_posix(),source_sha256=sha,role='BPR',variables=variables)
        for path,sha in bor.SOURCES.values()],owner_id=owner,namespace=mapping)))
    code={name:pin(ROOT/name) for name in CODE}
    receipt=dict(status='STARTED',owner=owner,namespace=mapping,setup=setup,source_pins=bor.SOURCES,
        code_pins=code,scope='four bounded rollback fixtures; no engine/day; no ordering waiver',cases=[])
    with output.open('x',encoding='utf-8') as stream:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                with isolation.connection('VFTEST_BPR') as raw:
                    receipt['native_context']=native_context(raw,isolation)
                    fixture_cases=list(cases())
                    if selected is not None:
                        if not selected or not set(selected) <= {item[0] for item in fixture_cases}:
                            raise ValueError('Unknown bounded BOR fixture selection')
                        fixture_cases=[item for item in fixture_cases if item[0] in selected]
                    receipt['selected_cases']=[item[0] for item in fixture_cases]
                    receipt['preflight']=preflight_fixtures(BorFixtureSQL(raw,isolation),
                        [(item[0],item[-1]) for item in fixture_cases])
                    if receipt['preflight']['status']!='PASS':
                        raise ValueError('BOR fixture preflight failed before mutation')
                    for name,source,report,history,rrr_history,declared in fixture_cases:
                        sql=BorFixtureSQL(raw,isolation)
                        originals={key:sql.rows(*key) for key in declared}
                        scratch=sql.scratch()
                        case=dict(name=name,fixtures=[dict(role=k[0],table=k[1],rows=storage(v))
                            for k,v in declared.items()],sql=[],comparisons={})
                        receipt['cases'].append(case)
                        raw.raw.autocommit=False
                        try:
                            for key,rows in declared.items():
                                sql.load(*key,rows)
                            case['filler_policy']=sql.fills
                            rows=bor.collect_bor_order_allocation(**source,equal=ascii_equal)
                            execute_native(raw,scripts['collect'],isolation,case['sql'])
                            case['comparisons']['BORWithOrderAllocation']=strict_rows(sql,('BPR','BORWithOrderAllocation'),rows)
                            projection=bor.generate_bor_order_allocation(bor_rows=rows,**report,equal=ascii_equal)
                            execute_native(raw,scripts['report'],isolation,case['sql'])
                            native=[restore_resultset(item) for item in case['sql'][-1]['resultsets']]
                            expected=[list(map(list,projection['header_resultset'])),list(map(list,projection['data_resultset']))]
                            case['report']=dict(status='PASS' if native==expected else 'FAIL',
                                native=storage(native),modern=storage(expected),policy='exact ordinal cells and header')
                            for key,current,opening,function in (
                                ('bor_history',rows,history,bor.collect_bor_order_allocation_history),
                                ('rrr_history',[],rrr_history,bor.collect_rrr_order_allocation_history)):
                                args=dict(opening_history=opening,business_date=TODAY.isoformat(),horizon=90)
                                args['current_bor' if key=='bor_history' else 'current_rrr']=current
                                expected_history=function(**args)
                                execute_native(raw,scripts[key],isolation,case['sql'])
                                table='BOR_OrderAllocationHistory' if key=='bor_history' else 'RRR_OrderAllocationHistory'
                                case['comparisons'][table]=strict_rows(sql,('BPR',table),expected_history)
                            expected_flags=[{**row,'IsScriptExecuted':True} for row in declared[('Importer','ScriptExecutedFlag')]]
                            case['comparisons']['ScriptExecutedFlag']=strict_rows(sql,('Importer','ScriptExecutedFlag'),expected_flags)
                            if any(sql.scratch().values()):
                                raise ValueError('Canonical final scratch clearing differs')
                            case['status']='PASS' if (case['report']['status']=='PASS' and
                                all(value['status']=='PASS' for value in case['comparisons'].values())) else 'FAIL'
                        except Exception as error:
                            case.update(status='FAIL',error=type(error).__name__+': '+str(error))
                        finally:
                            raw.rollback(); raw.raw.autocommit=True
                        case['rollback']={'.'.join(key):strict_rows(sql,key,rows) for key,rows in originals.items()}
                        case['scratch_rollback']={name:strict_rows(sql,('Intermediate',name),rows)
                                                 for name,rows in scratch.items()}
                        if raw.execute('SELECT @@TRANCOUNT').fetchval()!=0 or any(
                            item['status']!='PASS' for item in (*case['rollback'].values(),*case['scratch_rollback'].values())):
                            raise ValueError('BOR rollback did not preserve complete touched populations')
            receipt['status']='PASS' if all(case['status']=='PASS' for case in receipt['cases']) else 'FAIL'
        except Exception as error:
            receipt.update(status='FAIL',error=type(error).__name__+': '+str(error))
        finally:
            receipt['code_identity_unchanged']=code=={name:pin(ROOT/name) for name in CODE}
            receipt['source_identity_unchanged']=all(pin(SOURCE/path)==sha for path,sha in bor.SOURCES.values())
            if not receipt['code_identity_unchanged'] or not receipt['source_identity_unchanged']:
                receipt.update(status='FAIL',error='Source/code identity changed')
            json.dump(storage(receipt),stream,indent=2,ensure_ascii=False,allow_nan=False)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--cases',nargs='+')
    args=parser.parse_args()
    result=run(args.owner,args.output,args.cases)
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']),error=result.get('error'))))
    raise SystemExit(result['status']!='PASS')
