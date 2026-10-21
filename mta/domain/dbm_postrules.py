"""Canonical discard and suggestion/spike history producers.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date,datetime
from itertools import chain
from mta.row_sequences import history_rows
from mta.domain.ordinal_lookup import OrderedIndex
from mta.domain.sql_identity_keys import row_join_key


def _day(today,state):
    value=today.isoformat() if isinstance(today,date) else today
    runs=state['LastBatchRunTbl']
    if len(runs)!=1 or str(runs[0]['LastRunDate']).replace(' ','T')!=value+'T00:00:00':
        raise ValueError('Post-rules require singleton midnight business date')
    return value


def _key(row):return row_join_key(row)


def _raw_key(row):
    return (row['SKUCode'],row.get('WhCode',row.get('WHCode'))) if 'SKUCode' in row else None


def _different(suggestions,masters):
    if not masters:return list(suggestions)
    result=[]
    with OrderedIndex(masters) as index:
        for r in suggestions:
            if not any(_key(m)==_key(r) and m['Norm']==r['NewNorm']
                       for m in index.candidates(_raw_key(r))):result.append(r)
    return result


def discard_suggestions(today,state):
    today=_day(today,state);result=deepcopy(state)
    suggestions=_different(result['Suggestions'],state['DBMMaster'])
    keys=set()
    with OrderedIndex(state['DBMMaster']) as index:
        for r in suggestions:
            for m in index.candidates(_raw_key(r)):
                if (_key(r)==_key(m) and r['Type']!=12 and r['NewNorm']<m['MinNorm']
                        and r['NewNorm']<m['Norm']):keys.add(_key(r))
    discarded=({'SKUCode':r['SKUCode'],'WhCode':r['WhCode'],'SuggestionType':r['Type'],'SuggestionDate':today,'DiscardCode':4}
        for r in suggestions if _key(r) in keys)
    from mta.application.native_output_contracts import validated_new_rows
    discarded=validated_new_rows(discarded,'DBM/DiscardedSuggestions',stage='postrules/discarded')
    result['DiscardedSuggestions']=history_rows(chain(
        (r for r in result['DiscardedSuggestions'] if str(r['SuggestionDate'])!=today),discarded),
        like=state['DiscardedSuggestions'])
    result['Suggestions']=[r for r in suggestions if _key(r) not in keys]
    return result


def generate_reports(today,state):
    today=_day(today,state);result=deepcopy(state)
    result['Suggestions']=_different(result['Suggestions'],state['DBMMaster'])
    current=[]
    with OrderedIndex(result['Suggestions']) as index:
        for m in state['DBMMaster']:
            for r in index.candidates(_raw_key(m)):
                if _key(m)==_key(r):current.append({'SKUCode':m['SKUCode'],'WhCode':m['WhCode'],
                    'Type':r['Type'],'OldNorm':m['Norm'],'NewNorm':r['NewNorm'],
                    'SuggestionDate':today})
    from mta.application.native_output_contracts import validate_produced_rows
    validate_produced_rows(current,'DBM/SuggestionsLog',stage='postrules/suggestions-log')
    result['SuggestionsLog']=history_rows(chain(
        (r for r in result['SuggestionsLog'] if str(r['SuggestionDate'])!=today),current),
        like=state['SuggestionsLog'])
    spikes=[{'SKUCode':r['SKUCode'],'WhCode':r['WhCode'],'SuspendFromDate':r['WaitStartDate'],'SuspendTillDate':r['WaitTillDate']}
        for r in state['SuspendSpikeTbl'] if str(r['WaitStartDate'])==today]
    validate_produced_rows(spikes,'DBM/SpikeReport',stage='postrules/spike-report')
    result['SpikeReport']=history_rows(chain(
        (r for r in result['SpikeReport'] if str(r['SuspendFromDate'])!=today),spikes),
        like=state['SpikeReport'])
    return result


def postrule_stages(today,state):
    discarded=discard_suggestions(today,state)
    final=generate_reports(today,discarded)
    return [('discard',discarded),('reports',final)]


def calculate_postrules(today,state):
    stages=postrule_stages(today,state)
    return {**stages[-1][1],'PostruleStages':[{'stage':n,'state':s} for n,s in stages]}
