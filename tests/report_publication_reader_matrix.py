"""Finite report-build-to-consumer qualification, called by the owned proof.

Direct handlers exercise unchanged wire formatting; no browser or service is
started. Complete bodies, source identities and actual dispatch stay external.
"""
from copy import deepcopy
from contextlib import ExitStack
import gzip
import importlib
import inspect
import json
from time import perf_counter
from unittest.mock import patch


def qualify(run,publication,root,payload):
    from django.test import override_settings
    from mta.presentation import views,context
    from mta.serialization import digest
    root.mkdir(exist_ok=True)
    cases=[]
    def add(name,handler,module,function,extra=None,**options):
        cases.append((name,handler,module,function,{**deepcopy(payload),**(extra or {})},options))
    add('bpr-grid',views.bpr_data,'bpr_prepared','read_bpr')
    add('bpr-count',views.bpr_data,'bpr_prepared','read_bpr',count=True)
    add('bpr-analytics',views.bpr_analytics,'bpr_prepared','read_bpr',{'name':'BPR'})
    add('rrr-grid',views.rrr_data,'rrr_prepared_sql','read_prepared')
    add('rrr-count',views.rrr_data,'rrr_prepared_sql','read_prepared',count=True)
    for branch in ('tech','eco'):
        add('btr-'+branch,views.btr_data,'btr_snapshot','read_snapshot',
            {'name':branch,'displayPrepared':True,'displayHorizon':90})
        add('buffer-'+branch,views.buffer_trends,'history_prepared_sql','read_graph',
            {'bufferTrendType':branch,'Days':7})
    masters=run.production_manifest['images']['reports/bpr/vf_RationedReqReport']
    from mta.presentation.selective import image_rows
    row=next(iter(image_rows(run,masters['image'])))
    pair=dict(SKUCode=row['SKUCode'],WhCode=row['WhCode'])
    add('research-pair-parent',views.research_insights,'history_prepared_sql','read_research',{'Data':[pair]})
    add('historical-availability',views.historical_availability,'history_prepared_sql','read_historical_availability')
    for kind in ('loc','sku','pie','ageing'):
        add('guided-dbm-'+kind,views._insight_data,'guided_dbm','read_guided_dbm',kind=kind)
    add('chronic-grid',views._insight_data,'guided_chronic','read_guided_chronic',kind='chronic-grid')
    for kind in ('chronic-loc','chronic-sku'):
        add(kind,views._insight_data,'chronic_sql','read_chronic',kind=kind)
    for kind in ('availability-trend','availability-ageing','excess-sku','excess-value'):
        add(kind,views._insight_data,'guided_history_prepared','read_prepared',{'horizon':90,'horison':90},kind=kind)
    add('planning-overview',views.planning_overview,'planning_summary','read')
    for category in ('excessInventory','orderFulfillment'):
        add(category+'-grid',views.planning_grid,'planning_grid_sql','read_grid',{'category':category})
        add(category+'-count',views.planning_grid,'planning_grid_sql','read_grid',{'category':category},count=True)
        add(category+'-chart',views.planning_graph,'planning_chart_sql','graph',{'category':category})
        add(category+'-custom',views.planning_custom,'planning_custom_sql','custom_grid',{'category':category})
    for direction in ('parent','child'):
        add('expedite-'+direction+'-chart',views.planning_graph,'planning_expedite_chart_sql','queries',
            {'category':'expedite','type':direction})
        add('git-'+direction+'-grid',views.planning_grid,'planning_git_sql','grid',{'category':'git','type':direction})
    add('git-child-chart',views.planning_graph,'daily_git_read','graph',{'category':'git','type':'child'})
    add('git-custom',views.planning_custom,'daily_git_custom','custom',{'category':'git','type':'custom'})
    add('shared-daily-graph',views.history_graph,'dbm_read','_history_pair',
        {'SKUCode':pair['SKUCode'],'WHCode':pair['WhCode']})
    result=[]
    # The owning harness binds a candidate in process for this isolated fixture
    # only. Every read still uses actual selected-run identity/seal checks.
    for name,handler,module,function,request,options in cases:
        started=perf_counter();target=importlib.import_module('mta.presentation.'+module)
        with patch.object(target,function,wraps=getattr(target,function)) as dispatch:
            response=inspect.unwrap(handler)(None,request,**options)
        if not dispatch.called:
            # Native BTR retains the explicitly qualified v1 fallback for
            # ambiguous sources; never invent a unique-source display bag.
            fallback=publication.layers['btr']['receipt'].get('display_fallback')
            if not (name.startswith('btr-') and fallback=='normalized_source_ambiguity'):
                raise AssertionError('Prepared dispatch absent: '+name)
        body=json.loads(response.content)
        if response.status_code!=200 or body.get('status',200)!=200:
            raise AssertionError('Report wire failure: '+name+' '+repr(body))
        with gzip.open(root/(name+'.json.gz'),'wt',encoding='utf-8') as stream:
            json.dump(body,stream,ensure_ascii=False,allow_nan=False)
        result.append(dict(case=name,reader=module+'.'+function,dispatches=dispatch.call_count,
            run=str(run.pk),business_date=str(run.business_date),publication_seal=publication.seal_digest,
            full_body_digest=digest(body),seconds=perf_counter()-started))
        (root/'progress.json').write_text(json.dumps(result,indent=2))
    # Counts/export deliberately retain the BTR v1 relation even when display
    # is v2. Export whole typed rows and compare the v1/v2 selected bundles.
    from mta.presentation import btr_sql,rrr_sql,btr_snapshot
    from mta.runtime.models import BtrReportingGeneration
    generation=BtrReportingGeneration.objects.get(pk=publication.layers['btr']['receipt']['generation'])
    reference=btr_snapshot.reference_generation(run,generation) if generation.version==2 else generation
    for branch in ('tech','eco'):
        outputs=[]
        for selected in (reference,generation):
            with override_settings(VF_BTR_REPORTING_GENERATION=str(selected.pk)):
                rows,dates=btr_sql.read_btr(run,{**payload,'name':branch},paging=None,export=True)
                outputs.append(dict(rows=list(rows),dates=dates,
                    counts=btr_sql.read_btr(run,{**payload,'name':branch},paging=(1,50),count=True)))
        if outputs[0]!=outputs[1]:raise AssertionError('BTR export/count reference differs')
        with gzip.open(root/('btr-'+branch+'-export.json.gz'),'wt',encoding='utf-8') as stream:
            json.dump(outputs[1],stream,ensure_ascii=False,allow_nan=False)
        result.append(dict(case='btr-'+branch+'-count-export',full_body_digest=digest(outputs[1])))
    rrr=rrr_sql.read_rrr(run,payload,paging=None,count=False)
    with gzip.open(root/'rrr-export.json.gz','wt',encoding='utf-8') as stream:
        json.dump(rrr,stream,ensure_ascii=False,allow_nan=False)
    result.append(dict(case='rrr-export',full_body_digest=digest(rrr)))
    (root/'result.json').write_text(json.dumps(dict(status='PASS',cases=result),indent=2))
    return result
