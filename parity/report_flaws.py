"""Explicit non-parity disposition, never a repair of unordered legacy text.

Only independently evidenced ambiguous Norm0/horizon30 occurrence text is
uncomparable. All populations, multiplicity and every other value remain exact.
Raw legacy values are retained in the result, not copied to modern state.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, timedelta
import hashlib
from pathlib import Path
import re

from mta.serialization import digest
from parity.temporal import differences

SCOPE_DIGEST='29aefae1bac79839dbeedc3ad2dd8a04f72d24038dd9f53f102a3f94bfb9e77a'
MARKER={'unproven_field':'LEG-NORM0-OCCURRENCE-ORDER'}


def validate_scope(scope, input_sha256, *, verify_sources=False):
    if digest(scope)!=SCOPE_DIGEST or scope['evidence']['input_sha256']!=input_sha256:
        raise ValueError('Report limitation is not the pinned same-input Norm0/horizon30 disposition')
    if verify_sources:
        for name in ('source','retained_receipt'):
            item=scope['evidence']
            if hashlib.sha256(Path(item[name]).read_bytes()).hexdigest()!=item[name+'_sha256']:
                raise ValueError('Legacy flaw source/receipt changed: '+name)


def ambiguous_fragments(state, today):
    """Canonical Norm0 image/window/positive-fragment membership, not modern NULLs."""
    day=date.fromisoformat(today)
    descriptions=Counter(row['SKUCode'] for row in state['SKUDescriptionTbl'])
    image=Counter()
    for master in state['DBMMaster']:
        if master['Norm']==0:
            image[master['SKUCode'],master['WhCode']]+=descriptions[master['SKUCode']]
    fragments=defaultdict(Counter)
    for row in state['DailyConsumption']:
        key=row['SKUCode'],row['WhCode']
        observed=date.fromisoformat(row['ReportDate'][:10])
        if image[key] and observed>day-timedelta(days=30) and row['Consumption']>0:
            value='['+observed.strftime('%d/%m/%y')+' - '+str(row['Consumption'])+']'
            fragments[key][value]+=image[key]
    return {key:values for key,values in fragments.items() if len(values)>1}


def compare_reports(left, right, canonical_state, today, scope):
    validate_scope(scope,scope['evidence']['input_sha256'])
    ambiguous=ambiguous_fragments(canonical_state,today)
    summary=left['norm0-data']['Norm0Norm1Norm2Report']
    observed=set()
    for row in summary:
        key=row['SKUCode'],row['WHCode']
        if key not in ambiguous:continue
        raw=row['Occurances']
        if not isinstance(raw,str):raise ValueError('Ambiguous legacy text is unexpectedly absent')
        parts=re.findall(r'\[[^\]]+\]',raw)
        remainder=re.sub(r'\[[^\]]+\]','',raw)
        if Counter(parts)!=ambiguous[key] or remainder.strip(' ,'):
            raise ValueError('Legacy raw occurrence content differs from its source observations')
        if row['Count']!=sum(ambiguous[key].values()):
            raise ValueError('Legacy positive count differs from occurrence membership')
        observed.add(key)
    if observed!=set(ambiguous):raise ValueError('Canonical ambiguity summary population differs')

    raw_values=[]
    def projection(reports,side):
        output=deepcopy(reports)
        for stage,tables in output.items():
            if not stage.startswith(('norm0-','norm1-','norm2-')):continue
            for table,warehouse in (('Norm0Norm1Norm2Report','WHCode'),('Norm0_1_2ReportDetails','WhCode')):
                for row in tables.get(table,[]):
                    key=row['SKUCode'],row[warehouse]
                    if key not in ambiguous:continue
                    raw=row['Occurances']
                    if side=='modern' and raw is not None:
                        raise ValueError('Modern ambiguous occurrence text must remain unavailable, not invented')
                    raw_values.append(dict(side=side,stage=stage,table=table,SKUCode=key[0],WhCode=key[1],
                                           field='Occurances',raw_value=raw))
                    row['Occurances']=MARKER
            # Exports persist until the next export, including norm1's early
            # stages. The nine-column shape and proven Norm0 keys bind this to
            # the same carried display field, not a whole report exclusion.
            for row in tables.get('ReportRows',[]):
                values=row['values']
                if len(values)!=9:continue
                key=str(values[0]),str(values[2])
                if key not in ambiguous:continue
                raw=values[8]
                if side=='modern' and raw!=' ':
                    raise ValueError('Modern excluded export text differs from its unavailable representation')
                raw_values.append(dict(side=side,stage=stage,table='ReportRows',SKUCode=key[0],WhCode=key[1],
                                       field='Occurances',raw_value=raw))
                values[8]=MARKER
        return output
    delta=differences(projection(left,'legacy'),projection(right,'modern'),'/emitted-reports')
    return dict(status='FAIL' if delta else 'LEGACY_FLAW' if ambiguous else 'PASS',
                deterministic_status='FAIL' if delta else 'PASS',differences=delta,
                parity_claim_for_affected_field=False,legacy_flaw=scope['evidence']['id'],
                affected_identities=[list(key) for key in sorted(ambiguous)],
                canonical_fragment_bags={key[0]+'@'+key[1]:dict(values) for key,values in ambiguous.items()},
                unproven_field='Occurances',raw_values=raw_values)
