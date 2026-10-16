"""Isolated TEMP-table PostgreSQL value/response probe, never a case workflow.

Run on an owned runtime via stdin. It connects ONLY to the maintenance database
postgres, creates session-local TEMP tables, redirects model table metadata in
this process, rolls everything back and closes. No production table is written;
this does not certify production ownership triggers or a live business action.
"""
import hashlib
import json
import os
from datetime import date
from unittest.mock import patch

os.environ['VF_DB_NAME'] = 'postgres'
os.environ['DJANGO_SETTINGS_MODULE'] = 'vectorflow.settings'
import django
django.setup()
from django.db import connection, transaction
from django.db.models import NOT_PROVIDED, Value
from mta.runtime.mdm_models import MdmSource, MdmTask, MdmSubTask, MdmSkuDescription, MdmLocationDescription
from mta.runtime.mdm_season_models import MdmSeasonRequested, MdmSeasonHistory, MdmSeasonQueue
from mta.runtime.mdm_skuloc_models import MdmSkuLocAddRequested
from mta.runtime.mdm_phase_controls_models import MdmPhaseOutRequested, MdmPhaseOutHistory
from mta.mdm import season_tasks, season_reads, phase_controls_tasks
from mta.serialization import storage

result = {'boundary': 'TEMP typed storage + actual seasonal projection/queue value writer; not production trigger/permission/day proof', 'checks': []}
models = [MdmTask,MdmSubTask,MdmSkuDescription,MdmLocationDescription,MdmSeasonRequested,MdmSeasonHistory,MdmSeasonQueue,MdmSkuLocAddRequested,MdmPhaseOutRequested,MdmPhaseOutHistory]
original_tables = {m:m._meta.db_table for m in models}


def check(name, actual, expected):
    assert actual == expected, (name, actual, expected)
    result['checks'].append({'name':name,'actual':storage(actual),'expected':storage(expected),'status':'PASS'})


try:
    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute("SET LOCAL lock_timeout='2s'")
            cur.execute("SET LOCAL statement_timeout='15s'")
            cur.execute('SELECT current_database(),current_user,pg_backend_pid()')
            result['identity']=list(cur.fetchone())
            assert result['identity'][0]=='postgres'
            assert result['identity'][1]=='handoff3005_s2_consumer'
            # All generated identifiers are fixed model class names, no user SQL.
            for model in models:
                table='contract_'+model.__name__.lower()
                columns=[]
                for field in model._meta.local_fields:
                    kind='bigserial' if field.primary_key else field.db_type(connection)
                    sql=connection.ops.quote_name(field.column)+' '+kind
                    if field.primary_key: sql+=' PRIMARY KEY'
                    elif not field.null: sql+=' NOT NULL'
                    if field.db_default is not NOT_PROVIDED:
                        default=field.db_default
                        if isinstance(default,Value):default=default.value
                        assert isinstance(default,(int,bool)),repr(default)
                        sql+=' DEFAULT '+('true' if default is True else 'false' if default is False else str(default))
                    columns.append(sql)
                cur.execute('CREATE TEMP TABLE '+connection.ops.quote_name(table)+' ('+','.join(columns)+') ON COMMIT DROP')
                model._meta.db_table='"pg_temp"."'+table+'"'
            cur.execute('SELECT nspname FROM pg_namespace WHERE oid=pg_my_temp_schema()')
            result['temporary_schema']=cur.fetchone()[0]
        source=MdmSource(pk=990001)
        common=dict(sc='5954',wc='DP020819',sd='2026-10-21',dnp='50',ulc='195',bd='9')
        result['vectors']=[]
        for label,end,expected in [('blank','',date(1900,1,1)),('null',None,None),('finite','2026-10-30',date(2026,10,30))]:
            task_id='isolated-contract-'+label
            payload={**common,'ed':end}
            converted=season_tasks.convert(payload,list(payload),12)
            row=MdmSeasonRequested.objects.create(source_id=source.pk,**converted,TaskId=task_id,ActionType=2,Approved=False,Reverted=False,ActivateDBM=False)
            row.refresh_from_db();check(label+' typed EndDate',row.EndDate,expected)
            MdmSeasonHistory.objects.create(source_id=source.pk,**converted,TaskId=task_id,ActionType=2,ApproverId='2')
            MdmTask.objects.create(source_id=source.pk,TaskID=task_id,MasterId='12',ColumnList=','.join(converted),RequesterId='1')
            with patch.object(season_reads,'_scope_count',return_value=1):
                reviewed=season_reads.details(source,{'taskId':task_id},{'id':'2'})
                denied=season_reads.details(source,{'taskId':task_id},{'id':'other'})
            check(label+' unassigned reviewer has no rows',denied,[{'MasterId':12,'data':[]}])
            check(label+' reviewer end-date presence','ed' in reviewed[0]['data'][0],expected is not None)
            if expected is not None:check(label+' reviewer exact date',reviewed[0]['data'][0]['ed'],expected)
            # Pure effect writer only, redirected to TEMP tables. No real submit,
            # approval endpoint, decision decorator, source/owner or run mutation.
            row.Approved=True
            season_tasks._effect(source,12,[row])
            queued=MdmSeasonQueue.objects.get(source_id=source.pk)
            check(label+' queue preserves exact end-date',queued.EndDate,expected)
            check(label+' queue delta/cap/buildup',(queued.DeltaNormPercentage,queued.UpperLowerCap,queued.BuildupDuration),(50,195,9))
            result['vectors'].append({'label':label,'wire':payload,'converted':storage(converted),'requested':storage({n:getattr(row,n) for n in converted}), 'reviewed':storage(reviewed),'queued':storage({n:getattr(queued,n) for n in converted}), 'consumer_classification_source':'ValidateSeasonalityData.sql:105 / seasonality_validation.py:231; not execute_day', 'finite_type':1 if queued.EndDate is not None else 2})
            MdmSeasonQueue.objects.all().delete()
        pair=MdmSkuLocAddRequested.objects.create(source_id=source.pk,SKUCode='6249',WhCode='DP010290',ParentWhCode='LDC001',TaskId='isolated-contract-default')
        pair.refresh_from_db()
        check('omitted Add StockPercentForRat database default',pair.StockPercentForRat,100)
        # H4: execute the actual submitter against TEMP tables with explicit
        # pair/scope/assignee stubs. This isolates row accounting from unrelated
        # catalogue installation; it does NOT claim scope/authentication proof.
        from unittest.mock import MagicMock
        pairs=MagicMock();pairs.values_list.return_value=[('337','DP010290')]
        actor={'id':'990001','name':'isolated contract probe'}
        payload={'id':7,'taskId':'','data':[{'sc':'337','wc':'DP010290'},{'sc':'337'}],'all_users':[]}
        with patch.object(phase_controls_tasks.MdmSkuLocPair.objects,'filter',return_value=pairs), patch.object(phase_controls_tasks,'_submission_scopes',return_value=({'337'},{'dp010290'})), patch.object(phase_controls_tasks,'_approvers',return_value=[{'id':'2','name':'isolated reviewer'}]):
            response=phase_controls_tasks.submit(source,payload,actor,1)
            check('native missing-key row is silently excluded, not falsely counted as error',response['errorCount'],'0')
            check('two submitted occurrences produce one requested occurrence',MdmPhaseOutRequested.objects.count(),1)
            check('requested/history occurrence conservation of keyed subset',MdmPhaseOutHistory.objects.count(),1)
            payload['data']=[{'sc':'337','wc':'DP010290','pi':'5954'},{'sc':'337','wc':'DP010290'}]
            payload['id']=8
            try:
                phase_controls_tasks.submit(source,payload,actor,1)
                missing_key_failed=False
            except KeyError:
                missing_key_failed=True
            check('later row lacking first-row column fails conversion',missing_key_failed,True)
            check('failed mixed-shape chunk added no request occurrences',MdmPhaseOutRequested.objects.count(),1)
        result['row_accounting_scope']='Real phase submitter; TEMP tables; pair membership/scopes/approvers stubbed; retained defect, no live workflow invoked'
        transaction.set_rollback(True)
    result['status']='PASS'
    result['transaction']='ROLLED_BACK'
finally:
    for model,table in original_tables.items():model._meta.db_table=table
    connection.close()
    result['connection_closed']=connection.connection is None
    result['source_hashes']={module.__name__:hashlib.sha256(open(module.__file__,'rb').read()).hexdigest() for module in (season_tasks,season_reads,phase_controls_tasks)}
    print(json.dumps(result,default=str))
