"""Read-only selective-reader regression against retained independent receipts.

The pre-action trial is explicitly reconstructed from its immutable original
rows with an empty command-view proxy. Stored actions are NOT removed, hidden
from serving, or rewritten. Current-action verification is separate below.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.db import connection
from django.test import Client, override_settings
from mta.presentation.context import selected_run, publication
from mta.presentation.dbm_read import dbm_context
from mta.presentation.daily_history import daily_graph
from mta.presentation import views
from mta.runtime.models import CalculationRun, RunCommand
from mta.serialization import digest
from parity.temporal import differences

ROOT = Path('/evidence')
TRIAL = ROOT / 'f3-dbm-gateway-002/proof'
ORACLE = ROOT / 'f3-dbm-filters-comparison-001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    return hashlib.sha256(json.dumps({'runs': list(CalculationRun.objects.order_by('pk').values(
        'id', 'status', 'input_digest', 'output_digest', 'production_digest', 'production_manifest')),
        'commands': list(RunCommand.objects.order_by('pk').values())}, sort_keys=True, default=str).encode()).hexdigest()


client = Client()
identity = {'HTTP_X_VECTORFLOW_IDENTITY': '{"id":"selective-read-proof"}'}
before = snapshot()
with connection.cursor() as cursor:
    cursor.execute("SET default_transaction_read_only=on")
    cursor.execute("SET statement_timeout='15s'")


def request(route, payload):
    response = client.post('/api/mta/' + route, json.dumps(payload), content_type='application/json', **identity)
    return response.status_code, response.json()


assert sha(ORACLE / 'receipt.json') == 'a9e9cc25d37316918f6322e88b9b78135f1315c8deabd2a30ac4d20abb7ef0e6'
assert sha(TRIAL / 'receipt.json') == '7c84d5e8021d7c7dc30aaadf0b267393918f48337525fcc1c4611b4049e95521'
old = json.loads((TRIAL / 'receipt.json').read_text())['dbm_filters']
oracle = json.loads((ORACLE / 'receipt.json').read_text())
expected_by_key = {(r['id'], r['route']): r for r in oracle['cases']}
assert sha(TRIAL / old['hierarchy_file']) == old['hierarchy_supplement']['sha256']
checks = []
trial_run = CalculationRun.objects.get(pk=old['run']['id'])
assert trial_run.output_digest == old['run']['output_digest']
empty_commands = SimpleNamespace(exists=lambda: False)
pre_action = SimpleNamespace(pk=trial_run.pk, business_date=trial_run.business_date,
    output_digest=trial_run.output_digest, production_manifest=trial_run.production_manifest, commands=empty_commands)
with override_settings(VF_MTA_HIERARCHY_FILE=str(TRIAL / old['hierarchy_file']),
        VF_MTA_HIERARCHY_SHA256=old['hierarchy_supplement']['sha256']), \
     patch('mta.presentation.context.read_outputs', side_effect=AssertionError('whole-run read')):
    with patch('mta.presentation.dbm_read.selected_run', return_value=pre_action):
        for entry in old['observations']:
            path = TRIAL / entry['file']
            assert sha(path) == entry['sha256']
            saved = json.loads(gzip.decompress(path.read_bytes()))
            status, response = request(saved['route'], saved['request'])
            expected_response = saved['response']
            # Retained actual-gateway error wraps the unchanged service body.
            # Unwrap only this exact transport contract, never consumer data.
            if saved['status'] == 503 and saved['transport'] == 'ACTUAL_COOKIE_GATEWAY_STORED_ROOTS':
                assert set(expected_response) == {'error', 'status_code', 'message'}
                assert expected_response['error'] == 'Failed to forward request' and expected_response['status_code'] == 503
                expected_response = json.loads(expected_response['message'])
            assert status == saved['status'] and digest(response) == digest(expected_response), (
                saved['case_id'], status, saved['status'], differences(expected_response, response, '/envelope'))
            independent = expected_by_key[saved['case_id'], saved['route']]
            if independent['status'] == 'PASS':
                path = ORACLE / independent['legacy_response']
                assert sha(path) == independent['legacy_response_sha256']
                expected = json.loads(gzip.decompress(path.read_bytes()))
                value = response['recordCount' if saved['route'] == 'DBMDataCount' else 'data']
                assert not differences(expected, value, '/consumer'), saved['case_id']
            else:
                assert independent['status'] == 'LEGACY_FLAW_NOT_PARITY' and status == 503
            checks.append({'id': saved['case_id'], 'route': saved['route'], 'status': independent['status']})

terminal = selected_run()
payload = {'product_permissions': [71001], 'location_permissions': [72001],
           'paginationParameter': {'pageNumber': 1, 'recordsPerPage': 5000}, 'filters': {}}
with patch('mta.presentation.context.read_outputs', side_effect=AssertionError('whole-run read')):
    status, count = request('DBMDataCount', payload)
    assert status == 200 and count['recordCount'] == '0'
    status, grid = request('DBMData', payload)
    assert status == 200 and grid['data'] is None
    current = dbm_context(history=True)
    history_root = ROOT / 'f3-daily-history-comparison-002'
    history_receipt = json.loads((history_root / 'receipt.json').read_text())
    assert history_receipt['status'] == 'PASS_ALL_TERMINAL_DAILY_HISTORY'
    history_path = history_root / 'legacy-daily-history.json.gz'
    assert sha(history_path) == 'aa9c0d207c56b3902fa782afad5ea591d4d38f9be02677d46a4328084c892bbb'
    expected = json.loads(gzip.decompress(history_path.read_bytes()))
    for row in expected:
        actual = daily_graph(current.dbm, row['SKUCode'], row['WhCode'])
        assert not differences(row['graph'], actual, '/history'), (row['SKUCode'], row['WhCode'])
    status, graph = request('DailyDataGraph', {**payload, 'SKUCode': '337', 'WHCode': 'AG515802'})
    assert status == 200 and graph['data'] == next(r['graph'] for r in expected if (r['SKUCode'], r['WhCode']) == ('337', 'AG515802'))
    status, denied = request('DailyDataGraph', {**payload, 'SKUCode': '337', 'WHCode': 'FORBIDDEN'})
    assert status == 200 and denied['data'] == []

# Integrity and current commands use actual stored lineage, not the pre-action proxy.
with override_settings(VF_MTA_PUBLISHED_RUN=str(trial_run.pk), VF_MTA_PUBLISHED_DIGEST=trial_run.output_digest,
        VF_MTA_HIERARCHY_FILE=str(TRIAL / old['hierarchy_file']),
        VF_MTA_HIERARCHY_SHA256=old['hierarchy_supplement']['sha256']):
    full = publication()
    selected = dbm_context()
    assert digest(full.dbm) == digest(selected.dbm)
    assert digest(views.dbm_filtered(full, payload)) == digest(views.dbm_filtered(selected, payload))
    actions = trial_run.commands.count()
    assert actions > 0
    del full, selected
assert before == snapshot()
print(json.dumps(dict(status='PASS_SELECTIVE_DBM_AND_HISTORY_RETAINED_ORACLES',
    pre_action_qualification='Private immutable pre-action read proxy only, no stored/serving action change',
    strict_pass=sum(c['status']=='PASS' for c in checks), legacy_flaws_not_parity=sum(c['status']!='PASS' for c in checks),
    dbm_contracts=checks, history_pairs=len(expected), history_rows=history_receipt['rows'],
    terminal_current_count=0, current_action_count=actions, action_full_state_digest_match=True,
    run=str(terminal.pk), output_digest=terminal.output_digest, production_digest=terminal.production_digest,
    existing_runs_commands_unchanged=True, persistent_writes=False, engine_replays=0,
    dbm_oracle_receipt_sha256=sha(ORACLE/'receipt.json'), history_oracle_sha256=sha(history_path))))
