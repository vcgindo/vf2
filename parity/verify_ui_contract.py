"""Selected deployed column/layout SQL against Fresh output; temp tables only."""
import json
import os
from pathlib import Path
import re
import sys
from parity.legacy_isolation import exclusive_replay, connection
from parity.output_archive import file_sha
from parity.temporal import differences

ROOT=Path('D:/freshvcf-build/evidence')
SOURCES={
    ROOT/'f3-ui-state-source-001/VectorFlowAPIs.VectorFlow.Processors.UIConfigProcessor.decompiled.cs':
        'f7ea223a1a101fe040158d4a7c6796090d2680100b7ce9cb03d97d8fe2faa6ff',
    ROOT/'f3-ui-state-source-001/VectorFlowAPIs.Filters.GenericFunction.decompiled.cs':
        '6850a0bf2eadb4a38a2998e96ef70a264a2bc529d0de5c433c066d76c1933420',
    ROOT/'f3-preview-source-001/VectorFlowAPIs.VectorFlow.Processors.Commons.CommonsProcessor.decompiled.cs':
        '6a79e4cd927c3a4bee0f72c9dab6f327bfcfcf9ef7dda21f1c906e8762be767b',
    Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/DBCreation/UI_ReportConfiguration_2.0.sql'):
        '4b248637cd659bdf05730964513bf555103d83521a268e93cddb24bc8c6f34da',
    Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/DBCreation/UI_ReportColumnTypes_2.0.sql'):
        '51883c78e5effbb55b303f07b99df9c84a3a336b0525d19b0540a9b95df02a19',
}


def main():
    modern_path=Path(sys.argv[1]); target=Path(sys.argv[2])
    target.mkdir(parents=True,exist_ok=False)
    result={'status':'FAILED','engine_replays':0,'permanent_sql_writes':False}
    try:
        for path,sha in SOURCES.items():
            if file_sha(path)!=sha:
                raise ValueError('Canonical source mismatch: '+str(path))
        modern=json.loads(modern_path.read_text())
        assert modern['status']=='POSTGRES_LAYOUT_SEQUENCE_PASS_COMPARISON_REQUIRED'
        for path,sha in modern['source_hashes'].items():
            assert file_sha(Path(path))==sha, path
        source=next(iter(SOURCES)).read_text()
        literals=re.findall(r'"(?:[^"\\]|\\.)*"',source.split('string.Concat(new string[5]',1)[1].split('string vectorPULLFG_BPR',1)[0])
        query=''.join(json.loads(s) for s in literals).replace('ui_ReportConfigurations','#Config').replace('.dbo.ui_ReportColumnTypes','#Types')
        query=query.replace("a.reportname= ''", "a.reportname= 'NormSuggestion'")
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                db.execute('SELECT TOP 0 * INTO #Config FROM dbo.ui_ReportConfigurations')
                db.execute('SELECT TOP 0 * INTO #Types FROM VFTEST_Importer.dbo.ui_ReportColumnTypes')
                db.execute('SELECT TOP 0 * INTO #Layouts FROM dbo.Userwise_UiReportConfiguration')
                for path,table,temp in ((list(SOURCES)[3],'ui_ReportConfigurations','#Config'),
                                        (list(SOURCES)[4],'ui_ReportColumnTypes','#Types')):
                    lines=[line.strip().replace('[dbo].['+table+']',temp) for line in path.read_text(encoding='utf-8-sig').splitlines()
                           if line.strip().startswith('INSERT') and "VALUES (N'NormSuggestion'," in line]
                    assert len(lines)==56
                    db.execute('\n'.join(lines))
                expected_config=json.loads(db.execute(query).fetchval())
                observed=[]
                user=modern['username']; report=modern['reportname']
                predicate=f"username='{user}' and reportname='{report}'"
                for item in modern['observations']:
                    action=item['action']; value=item['input_state']
                    if action=='GetState':
                        row=db.execute('select [state] from #Layouts where '+predicate).fetchone()
                        data='' if row is None else (row[0] or None)
                    else:
                        sql='delete from #Layouts where '+predicate+';'
                        if action=='SaveState':
                            sql+=f"Insert into #Layouts (username,reportname,state) values('{user}','{report}','{value or ''}')"
                        cursor=db.execute(sql)
                        count=cursor.rowcount
                        while cursor.nextset():
                            count+=max(cursor.rowcount,0)
                        data=str(count)
                    observed.append(dict(action=action,input_state=value,data=data))
                # Reproduce the source's unescaped-literal failure, not a repair.
                try:
                    db.execute(f"delete from #Layouts where {predicate}; Insert into #Layouts (username,reportname,state) values('{user}','{report}','user's layout')")
                except Exception as exc:
                    quoted_failure={'type':type(exc).__name__,'message':str(exc)}
                else:
                    raise AssertionError('Expected canonical quoted-literal failure')
        delta=differences(expected_config,modern['config'],'/DBM-UIConfig')+differences(observed,modern['observations'],'/layout-sequence')
        result.update(status='PASS_SELECTED_DBM_UI_LAYOUT' if not delta else 'FAIL',
            config_rows=len(expected_config),sequence_steps=len(observed),differences=delta,
            config=expected_config,observations=observed,query=query,quoted_literal_failure=quoted_failure,
            sources={str(p):s for p,s in SOURCES.items()},modern_sha256=file_sha(modern_path),
            qualification='Deployed SQL plus independently source-transcribed scalar/row-count envelope; not legacy HTTP. '
                'Selected sequential ASCII layout operations only. Quoted SQL failure and unordered conflicting duplicates are NOT_PARITY; no engine/data/action changes.')
    finally:
        (target/'receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','config_rows','sequence_steps','differences')}))
    if delta:
        raise SystemExit(1)


if __name__=='__main__':
    main()
