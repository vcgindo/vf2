"""Canonical discard and suggestion/spike history producers."""
from copy import deepcopy
from datetime import date,datetime


def _day(today,state):
    value=today.isoformat() if isinstance(today,date) else today
    runs=state['LastBatchRunTbl']
    if len(runs)!=1 or str(runs[0]['LastRunDate']).replace(' ','T')!=value+'T00:00:00':
        raise ValueError('Post-rules require singleton midnight business date')
    return value


def _key(row):return row['SKUCode'],row['WhCode']


def _different(suggestions,masters):
    return [r for r in suggestions if not any(_key(m)==_key(r) and m['Norm']==r['NewNorm'] for m in masters)]


def discard_suggestions(today,state):
    today=_day(today,state);result=deepcopy(state)
    suggestions=_different(result['Suggestions'],state['DBMMaster'])
    keys={_key(r) for r in suggestions for m in state['DBMMaster'] if _key(r)==_key(m)
        and r['Type']!=12 and r['NewNorm']<m['MinNorm'] and r['NewNorm']<m['Norm']}
    result['DiscardedSuggestions']=[r for r in result['DiscardedSuggestions'] if str(r['SuggestionDate'])!=today]+[
        {'SKUCode':r['SKUCode'],'WhCode':r['WhCode'],'SuggestionType':r['Type'],'SuggestionDate':today,'DiscardCode':4}
        for r in suggestions if _key(r) in keys]
    result['Suggestions']=[r for r in suggestions if _key(r) not in keys]
    return result


def generate_reports(today,state):
    today=_day(today,state);result=deepcopy(state)
    result['Suggestions']=_different(result['Suggestions'],state['DBMMaster'])
    result['SuggestionsLog']=[r for r in result['SuggestionsLog'] if str(r['SuggestionDate'])!=today]+[
        {'SKUCode':m['SKUCode'],'WhCode':m['WhCode'],'Type':r['Type'],'OldNorm':m['Norm'],
         'NewNorm':r['NewNorm'],'SuggestionDate':today}
        for m in state['DBMMaster'] for r in result['Suggestions'] if _key(m)==_key(r)]
    result['SpikeReport']=[r for r in result['SpikeReport'] if str(r['SuspendFromDate'])!=today]+[
        {'SKUCode':r['SKUCode'],'WhCode':r['WhCode'],'SuspendFromDate':r['WaitStartDate'],'SuspendTillDate':r['WaitTillDate']}
        for r in state['SuspendSpikeTbl'] if str(r['WaitStartDate'])==today]
    return result


def postrule_stages(today,state):
    discarded=discard_suggestions(today,state)
    final=generate_reports(today,discarded)
    return [('discard',discarded),('reports',final)]


def calculate_postrules(today,state):
    stages=postrule_stages(today,state)
    return {**stages[-1][1],'PostruleStages':[{'stage':n,'state':s} for n,s in stages]}
