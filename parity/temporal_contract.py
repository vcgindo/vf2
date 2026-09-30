"""Frozen selected capture contract, independent of editable modern rosters."""
import hashlib
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1]/'baseline/temporal-oracle-roster.json'
SHA256 = '3e73b654f8509d6ef597889eb18d1f2e3342d9588fdc915145e76edab74cd0d2'
if hashlib.sha256(PATH.read_bytes()).hexdigest() != SHA256:
    raise ValueError('Pinned temporal oracle roster differs')
CONTRACT = json.loads(PATH.read_text())


def validate_state(state, *, initial=False):
    expected = CONTRACT['tables'] if initial else CONTRACT['closing_tables']
    if set(state) != set(CONTRACT['sections']):
        raise ValueError('Temporal state section roster differs')
    for section, tables in expected.items():
        if not isinstance(state[section], dict) or set(state[section]) != set(tables):
            raise ValueError('Temporal state table roster differs: '+section)
    parameters = [r['Parameter'] for r in state['dbm']['VFSettings']]
    if sorted(parameters) != CONTRACT['dbm_settings_parameters']:
        raise ValueError('DBM selected setting roster differs')
    for section in ('dbm','controls'):
        scratch = state[section]['IntermediateTables']
        # Controls use a table-name dictionary, DBM uses typed row wrappers.
        names = list(scratch) if isinstance(scratch,dict) else [r['table'] for r in scratch]
        if sorted(names) != CONTRACT['scratch_tables']:
            raise ValueError('Temporal scratch roster differs: '+section)


def roster_map(records, key, expected, label):
    names = [row[key] for row in records]
    if names != list(expected):
        raise ValueError(label+' ordered roster/multiplicity differs')
    return {row[key]:row for row in records}
