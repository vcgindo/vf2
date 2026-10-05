"""Qualify April chart formatting and the exact retained label defect via DLL."""
import json,sys,subprocess,hashlib
from pathlib import Path
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from parity.verify_expedite_charts import SECTIONS
from mta.presentation.expedite_charts import response_from_dataset


def main():
    root=Path(sys.argv[1]).resolve()
    assert root.is_relative_to(Path('D:/freshvcf-build/evidence').resolve())
    report=json.loads((root/'comparison.json').read_text())
    assert report['status']=='BAGS_MATCH_ORDER_AND_WIRE_REQUIRE_QUALIFICATION'
    results=[]
    def invoke(name,kind,path):
        output=root/(name+'-dll.json')
        completed=subprocess.run(['pwsh','-NoProfile','-File','parity/invoke_legacy_quadrant.ps1',
            '-Processor','ExpediteProcessor','-Direction',kind,'-InputPath',str(path),'-OutputPath',str(output)],capture_output=True,text=True)
        (root/(name+'-dll.log')).write_text(completed.stdout+completed.stderr,encoding='utf-8')
        assert completed.returncode==0,(name,'DLL invocation failed')
        binary=json.loads(output.read_text(encoding='utf-8-sig'))
        assert binary['input_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
        return binary['response']
    key='maxPipelineInvBlackRedSKUWithRationedQuantityAvailableAtParentuiconfig'
    def receiving(value):return value['data']['expediteDispatches'][key]['data']
    for case in ('broad','leaf'):
        for kind in ('parent','child'):
            name=case+'-'+kind
            path=root/(name+'-dataset.json')
            dataset=json.loads(path.read_text())
            tables={family:t['rows'] for family,t in zip(SECTIONS[kind],dataset['tables'])}
            actual=invoke(name,kind,path)
            assert actual==response_from_dataset(tables,kind),(name,'Pure formatter differs')
            result=dict(case=case,kind=kind,pure_formatter='EXACT',rows=len(receiving(actual)))
            if kind=='parent':
                corrected=response_from_dataset(tables,kind,receiving_own_label=True)
                # Prove the approved amendment changes only receiving labels.
                restored=deepcopy(corrected)
                for modern,legacy in zip(receiving(restored),receiving(actual)):
                    modern['LogisticsLocation']=legacy['LogisticsLocation']
                assert restored==actual
                source={r['WhCode'].rstrip().casefold():r['LogisticsLocation'] for r in tables['receiving']}
                result['own_label_only']=True
                result['native_receiving_location_labels']=len(set(source.values()))
                result['changed_labels']=sum(a['LogisticsLocation']!=b['LogisticsLocation'] for a,b in zip(receiving(corrected),receiving(actual)))
            if case=='broad':
                reordered=deepcopy(dataset);reordered['tables'][0]['rows'].reverse()
                reverse=root/(name+'-reversed-dataset.json')
                reverse.write_text(json.dumps(reordered),encoding='utf-8')
                reversed_response=invoke(name+'-reversed',kind,reverse)
                changed=sum(a['LogisticsLocation']!=b['LogisticsLocation'] for a,b in zip(receiving(actual),receiving(reversed_response)))
                assert changed>0,(kind,'Reversal did not reproduce the retained label flaw')
                result['unordered_critical_reversal_changes_receiving_labels']=changed
            results.append(result)
    value=dict(status='FORMATTER_EXACT_PARENT_LABEL_ONLY_EXCEPTION_QUALIFIED_CHILD_FLAW_REPRODUCED',
               results=results,order_parity=False,qualification='SQL sequence differences remain explicitly unresolved; no tie-order exception is inferred.')
    (root/'formatter-comparison.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps(value))


if __name__=='__main__':main()
