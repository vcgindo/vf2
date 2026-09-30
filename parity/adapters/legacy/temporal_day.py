"""Canonical SQL producer for one connected Block3 calculation day.

The caller owns temporal composition and the selected DBM continuation.  This
adapter owns the independent SQL boundary through native UpdateBPR and returns
the complete state/facts needed by that continuation.  It never calls the
modern calculation producer or the reset-and-seed R1 convenience entry point.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import os

from parity.temporal_contract import CONTRACT, validate_state
from parity.adapters.legacy import runner, r1_runner
from parity.legacy_isolation import Cursor as BoundCursor, MAPPING
from parity.adapters.legacy.r1_daily_input import execute_daily_legacy, read_scripts as read_daily_scripts
from parity.adapters.legacy.r1_importer_master import (
    SCRIPT as MASTER_SCRIPT, SHA256 as MASTER_SHA256, execute_master_legacy,
    read_script as read_master_script,
)
from parity.adapters.legacy.r1_supplier_input import execute_supplier_legacy, read_scripts as read_supplier_scripts
from parity.adapters.legacy.temporal_support import BINDINGS as CONTROL_BINDINGS, SCRIPTS as CONTROL_SCRIPTS
from parity.adapters.legacy.temporal_support import _json, _write


NATIVE_STAGES = ('CollectDataForBPR.sql', 'PhysicalInventoryColour', 'GenerateBPR.sql', 'UpdateBPR.sql')
ORDER_STAGES = ('ImportSpikeOrders.sql', 'CalculateDD.sql')
ORDER_TABLES = ('BPRMaster', 'AdditionalMasterData', 'SpikeOrderData',
                'SpikeOrderClosureHistory', 'NewSpikeOrders', 'ElephantOrders', 'LastBatchRunTbl')
DBM_METADATA = ('SKUDescriptionTbl', 'SiteDescriptionTbl', 'SkuAttributeData',
                'LocationAttributeData', 'SkuLocAttributeData')
DAILY_PRIOR = CONTRACT['tables']['bpr']
IMPORTER_PRIOR = CONTRACT['tables']['importer']
SUPPLIER_STAGES = ('ValidateSOBData.sql', 'ValidateMOQDataRaw1.sql', 'ValidateMOQDataRaw2.sql', 'ResetFlags.sql')


def _plain(value):
    return json.loads(json.dumps(value, default=_json))


def execute_day(prior, opening_date, day, profile, evidence, *, evidence_prefix='', commands=(), initial=False, post_policy=None):
    """Execute the canonical producer chain for one business day.

    ``prior`` is either the frozen seven-section opening or this adapter's own
    previous closing (after the caller has appended the selected DBM terminal
    state).  No derived current-day answer is accepted from the caller.
    """
    if os.environ.get('VFTEST_PROFILE') != 'fresh':
        raise ValueError('VFTEST_PROFILE=fresh is mandatory')
    delivery = profile.get('delivery') is not None
    expected_prior = {'importer', 'importer_settings', 'bpr', 'supplier', 'orders', 'controls', 'dbm'}
    if delivery:
        expected_prior |= {'control_aux', 'btr', 'consumer_context', 'publication_context'}
    if set(prior) != expected_prior:
        raise ValueError('Complete seven-section canonical prior is required')
    if not delivery:
        raise ValueError('Fresh temporal oracle requires the complete selected delivery profile')
    validate_state(prior, initial=initial)
    today = day['business_date']
    now = today + 'T00:00:00'
    if date.fromisoformat(opening_date) >= date.fromisoformat(today):
        raise ValueError('Canonical predecessor date must precede the business date')
    if any(profile['daily']['shell_flags'].values()):
        raise ValueError('Frozen canonical daily shell flags must all be zero')

    master_entry = {
        'schema': 'r1-importer-master-input-v1', 'business_date': today,
        'run_timestamp': now, 'import_non_nms': profile['import_non_nms'],
        'settings': [{'Parameter': row['Parameter'], 'Value': int(row['Value'])}
                     for row in prior['importer_settings']
                     if row['Parameter'] in ('NMSActive', 'DBMActive', 'UpdatePWh_RLT_RCP_GCP')],
        'prior_provenance': {'kind': 'SYNTHETIC_PRIOR_IMPORTER',
                             'identity': 'own-seven-section-close', 'business_date': opening_date},
        'prior': deepcopy(prior['importer']), 'raw_master': deepcopy(day['raw_master']),
        'raw_non_nms': deepcopy(day['raw_non_nms']), 'raw_no_norm': deepcopy(day['raw_no_norm']),
    }
    # The typed importer boundary uses 0/1 for SQL BIT; this changes no value.
    for records in master_entry['prior'].values():
        for record in records:
            for key, value in record.items():
                if type(value) is bool:
                    record[key] = int(value)
    daily_entry = {'schema': 'r1-daily-input-v1', 'raw_daily_data': deepcopy(day['raw_daily']),
                   **deepcopy(profile['daily']), 'prior_bpr': {**deepcopy(prior['bpr']),
                   'opening_provenance': {'kind': 'SYNTHETIC_PRIOR_BPR_DAILY',
                                          'identity': 'own-seven-section-close',
                                          'business_date': opening_date}}}

    # Pin every source before the first mutation.
    read_master_script(master_entry)
    read_supplier_scripts(now)
    read_daily_scripts(now)
    for name in (*r1_runner.R1_MASTER_SCRIPTS, *CONTROL_SCRIPTS, *r1_runner.R1_SEQUENCE):
        r1_runner._read_script(name, force_from_ui=profile['force_flags']['from_ui'], run_timestamp=now)
    if delivery:
        from parity.adapters.legacy.temporal_delivery import DeliverySQL, OWNERS, prepare, replay_commands
        delivery_pins = prepare()

    evidence = Path(evidence) if evidence is not None else None
    with runner.connection('VFTEST_Importer') as owner:
        raw = owner.raw
        quote = lambda name: '[' + name.replace(']', ']]') + ']'
        table = lambda role, name: MAPPING['VFTEST_' + role] + '.dbo.' + quote(name)
        rosters = {database: [(r[0], r[1]) for r in raw.execute(
            'SELECT s.name,t.name FROM ' + database + '.sys.tables t JOIN ' + database
            + '.sys.schemas s ON t.schema_id=s.schema_id WHERE t.is_ms_shipped=0')]
            for database in MAPPING.values()}
        scratch = sorted(t for s, t in rosters[MAPPING['VFTEST_Intermediate']] if s == 'dbo')

        def rows(role, name, schema='dbo', *, native=False):
            cursor = raw.execute('SELECT * FROM ' + MAPPING['VFTEST_' + role] + '.'
                                 + quote(schema) + '.' + quote(name))
            fields = [('WhCode' if not native and c[0] == 'WHCode' and name in {b[1] for b in CONTROL_BINDINGS.values()}
                       else c[0]) for c in cursor.description]
            return [dict(zip(fields, record)) for record in cursor.fetchall()]

        def identity():
            record = raw.execute('SELECT CONVERT(bigint,seed_value),CONVERT(bigint,increment_value),'
                'CONVERT(bigint,last_value) FROM ' + MAPPING['VFTEST_BPR'] + '.sys.identity_columns '
                "WHERE object_id=OBJECT_ID('" + table('BPR', 'SpikeOrderData') + "')").fetchone()
            return [{'Seed': record[0], 'Increment': record[1], 'LastValue': record[2]}]

        def reseed(value):
            if type(value) is not int or not 1 <= value <= 2147483647:
                raise ValueError('Explicit used SpikeOrderData identity counter required')
            raw.execute("DBCC CHECKIDENT ('" + table('BPR', 'SpikeOrderData')
                        + "', RESEED, " + str(value) + ') WITH NO_INFOMSGS')

        def load(role, name, records, *, append=False, identity_insert=False):
            target = table(role, name)
            if not append:
                raw.execute('DELETE FROM ' + target)
            if identity_insert:
                raw.execute('SET IDENTITY_INSERT ' + target + ' ON')
            try:
                valid = {c[0].casefold() for c in raw.execute('SELECT TOP 0 * FROM ' + target).description}
                for record in records:
                    if not {key.casefold() for key in record} <= valid:
                        raise ValueError('Input field drift for ' + target)
                    raw.execute('INSERT INTO ' + target + ' (' + ','.join(map(quote, record))
                                + ') VALUES (' + ','.join('?' for _ in record) + ')', tuple(record.values()))
            finally:
                if identity_insert:
                    raw.execute('SET IDENTITY_INSERT ' + target + ' OFF')

        class Borrowed:
            def __init__(self, logical):
                self.database = 'master' if logical == 'master' else MAPPING[logical]

            def cursor(self):
                raw.execute('USE ' + self.database)
                return BoundCursor(raw.cursor())

            def execute(self, sql, *parameters):
                return self.cursor().execute(sql, *parameters)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

        def borrowed(logical='master'):
            return Borrowed(logical)

        def scratch_state():
            return {'dbo.' + name: rows('Intermediate', name) for name in scratch}

        def control_snapshot():
            state = {name: rows(*binding) for name, binding in CONTROL_BINDINGS.items()}
            state['IntermediateTables'] = scratch_state()
            return _plain(state)

        def order_snapshot():
            state = {name: rows('BPR', name) for name in ORDER_TABLES}
            state.update(DBMMaster=rows('DBM', 'DBMMaster'), PSOData=rows('Importer', 'PSOData'),
                         OrderIdentity=identity(), IntermediateTables=scratch_state())
            return _plain(state)

        def native_snapshot(late=False):
            names = ('BPR_Table', 'DailyConsumption', 'vf_RationedReqReport', 'LastBatchRunTbl') if late else (
                'DailyDataForBPR', 'PenetrationAndColor', 'BPRExceptions', 'BPR_Table', 'LastBatchRunTbl')
            state = {('BPRDailyConsumption' if name == 'DailyConsumption' else name): rows('BPR', name)
                     for name in names}
            state['IntermediateTables'] = scratch_state()
            return _plain(state)

        def dbm_state():
            state = {name: rows(OWNERS.get(name, 'DBM') if delivery else 'DBM', name, native=delivery)
                     for name in CONTRACT['tables']['dbm'] if name != 'IntermediateTables'}
            if delivery:
                selected_settings = {v['Parameter'] for v in prior['dbm']['VFSettings']}
                state['VFSettings'] = [r for r in state['VFSettings'] if r['Parameter'] in selected_settings]
            state['IntermediateTables'] = [{'table': 'dbo.' + name, 'rows': rows('Intermediate', name)}
                                           for name in scratch]
            return _plain(state)

        original_reset = runner._reset

        def reset_for_delivery():
            if not delivery:
                return original_reset()
            counts = {}
            for logical in runner.DATABASES:
                database = MAPPING[logical]
                for schema, name in rosters[database]:
                    # TRUNCATE erases the identity's used state. DBCC RESEED
                    # alone cannot restore last_value on an empty never-used
                    # table. DELETE preserves that state without adding rows.
                    operation = 'DELETE FROM ' if logical == 'VFTEST_BPR' and name == 'SpikeOrderData' else 'TRUNCATE TABLE '
                    runner.consume(raw.cursor().execute(operation + database + '.' + quote(schema) + '.' + quote(name)))
                counts[logical] = len(rosters[database])
            return counts

        result = None
        error = None
        raw.execute('BEGIN TRANSACTION')
        try:
            with patch.object(runner, 'connection', borrowed), patch.object(runner, '_reset', reset_for_delivery):
                validation = execute_master_legacy(master_entry)
                if validation['outcome'] != 'APPLIED':
                    raise ValueError('Canonical master validation did not apply: ' + validation['outcome'])
                supplier, supplier_receipt = execute_supplier_legacy(deepcopy(day['supplier_feeds']), now)
                if any(stage['outcome'] == 'SQL_ERROR' for stage in supplier.values()):
                    raise ValueError('Canonical supplier validation returned SQL_ERROR')
                daily, daily_receipt = execute_daily_legacy(daily_entry, today, now)
                if any(stage['outcome'] == 'SQL_ERROR' for stage in daily.values()):
                    raise ValueError('Canonical daily validation returned SQL_ERROR')

                # Restore this engine's prior DBM close, including the explicit
                # list-wrapper representation of all 178 scratch populations.
                for name, records in prior['dbm'].items():
                    if name != 'IntermediateTables':
                        load(OWNERS.get(name, 'DBM') if delivery else 'DBM', name, records)
                command_receipts = []
                if commands:
                    if not delivery: raise ValueError('Frozen command replay requires the complete delivery profile')
                    from parity.adapters.legacy.temporal_delivery import replay_commands
                    command_receipts = replay_commands(raw, commands)
                scratch_input = prior['dbm']['IntermediateTables']
                if not isinstance(scratch_input, list):
                    raise ValueError('DBM IntermediateTables must use list table/rows wrappers')
                scratch_by_name = {record['table']: record['rows'] for record in scratch_input}
                if set(scratch_by_name) != {'dbo.' + name for name in scratch}:
                    raise ValueError('DBM scratch roster drift')
                for name in scratch:
                    load('Intermediate', name, scratch_by_name['dbo.' + name])
                load('DBM', 'LastBatchRunTbl', [{'LastRunDate': now}])

                connected = (DeliverySQL(raw, load, rows, dbm_state, scratch_state,
                                         delivery_pins, today, profile)
                             if delivery else None)
                flag_scripts = (('InitialiseSkuLocStdAttributeData.sql', 'Importer'),
                                ('01. ImportMasterData.sql', 'DBM'),
                                *((name, 'DBM') for name in CONTROL_SCRIPTS))
                for name, module in flag_scripts:
                    raw.execute("IF NOT EXISTS (SELECT 1 FROM " + table('Importer', 'ScriptExecutedFlag')
                        + " WHERE ScriptName=?) INSERT INTO " + table('Importer', 'ScriptExecutedFlag')
                        + "(ScriptName,IsScriptExecuted,IsScriptCritical,ModuleName) VALUES (?,0,1,?)",
                        name, name, module)

                # Daily ImportMasterDataComponents.bat rebuilds this table from
                # both current raw-master populations before DBM and BTR run.
                # Execute the deployed source so every non-key attribute is
                # reset by TRUNCATE/INSERT exactly as in the canonical engine.
                if delivery:
                    connected.execute('Importer',
                                      'Scripts/Importer/InitialiseSkuLocStdAttributeData.sql')

                # ImportMasterData is the actual metadata/structure writer and
                # retains the prior DBM Norm according to canonical source.
                sql, import_master_receipt = r1_runner._read_script('01. ImportMasterData.sql', run_timestamp=now)
                raw.execute('USE ' + MAPPING['VFTEST_DBM'])
                runner.consume(BoundCursor(raw.cursor()).execute(sql))

                # Non-master control state not represented by the DBM close is
                # restored explicitly, then today's commands are appended.
                load('Importer', 'UIUploadLogFNC', prior['controls']['upload_log'])
                load('Importer', 'AcceptedNorms', day['accepted_feed'])
                load('Importer', 'ForceNormChange', day['new_force_requests'], append=True)
                control_stages, control_receipts = [], []
                if delivery:
                    control_stages.extend(connected.controls(prior, day, control_snapshot))
                for name in CONTROL_SCRIPTS:
                    sql, receipt = r1_runner._read_script(name,
                        force_from_ui=profile['force_flags']['from_ui'], run_timestamp=now)
                    raw.execute('USE ' + MAPPING[receipt['execution_database']])
                    runner.consume(BoundCursor(raw.cursor()).execute(sql))
                    control_receipts.append(receipt)
                    if delivery:
                        connected.after_control(name)
                    control_stages.append((name, {**control_snapshot(), **connected.aux()} if delivery else control_snapshot()))
                if delivery:
                    control_stages.append(connected.finish_controls(control_snapshot))
                post_control_dbm_master = rows('DBM', 'DBMMaster')

                # Current source/configuration facts required by unchanged BPR
                # SQL.  None is a current-day calculated answer.
                load('BPR', 'SOBData', prior['supplier']['SOBData'])
                load('BPR', 'MOQData', prior['supplier']['MOQData'])
                load('BPR', 'SpikeOrderData', prior['orders']['SpikeOrderData'], identity_insert=True)
                load('BPR', 'SpikeOrderClosureHistory', prior['orders']['SpikeOrderClosureHistory'])
                load('BPR', 'NewSpikeOrders', prior['orders']['NewSpikeOrders'])
                load('BPR', 'ElephantOrders', prior['orders']['ElephantOrders'])
                reseed(prior['orders']['OrderIdentity'][0]['LastValue'])
                if delivery and identity() != prior['orders']['OrderIdentity']:
                    raise ValueError('Canonical loader did not preserve the declared opening order identity')
                load('BPR', 'LastBatchRunTbl', [{'LastRunDate': now if delivery else opening_date + 'T00:00:00'}])
                load('Importer', 'PSOData', day['order_feed'])

                calculation = profile['calculation']
                raw.execute('USE ' + MAPPING['VFTEST_Importer'])
                raw.execute("INSERT INTO " + table('Importer', 'ImporterSettingsTbl')
                            + "(Parameter,Value) VALUES ('StockReservationType',?)",
                            str(calculation['stock_configuration']['reservation_type']))
                for name in r1_runner.R1_SEQUENCE:
                    raw.execute("IF NOT EXISTS (SELECT 1 FROM " + table('Importer', 'ScriptExecutedFlag')
                        + " WHERE ScriptName=?) INSERT INTO " + table('Importer', 'ScriptExecutedFlag')
                        + "(ScriptName,IsScriptExecuted,IsScriptCritical,ModuleName) VALUES (?,0,1,'BPR')", name, name)
                settings = [('QtyReservationForRationingOnly', str(int(calculation['stock_configuration']['reservation_for_rationing_only']))),
                            ('StockThresholdForAdvOrderAlloc', calculation['allocation']['advance_stock_threshold_percent'])]
                for key, field in (('SpikeThresholdForHighNorm', 'spike_high'), ('SpikeThresholdForLowNorm', 'spike_low'),
                                   ('PSOThresholdForHighNorm', 'pso_high'), ('PSOThresholdForLowNorm', 'pso_low')):
                    values = {Decimal(row['policy'][field]) for row in calculation['policies']}
                    if len(values) != 1:
                        raise ValueError('Canonical BPR setting is global: ' + field)
                    settings.append((key, str(values.pop())))
                for key, value in settings:
                    raw.execute('INSERT INTO ' + table('BPR', 'BPRSettingsTbl') + '(Parameter,Value) VALUES (?,?)', key, value)
                for sequence, colour in enumerate(('Black', 'Red', 'Yellow', 'Green', 'Blue', 'White', 'Grey'), 1):
                    raw.execute('INSERT INTO ' + table('BPR', 'ColorSequence') + '(Color,SequenceNo) VALUES (?,?)', colour, sequence)
                openings = {(r['sku_code'], r['location_code']): r for r in calculation['stock_openings']}
                for policy in calculation['policies']:
                    key = (policy['sku_code'], policy['location_code']); opening = openings[key]
                    raw.execute('INSERT INTO ' + table('Importer', 'AdditionalDailyData')
                        + '(SKUCode,WhCode,UtilizedStock,StockForRationing,ReportDate) VALUES (?,?,?,?,?)',
                        key[0], key[1], opening.get('utilized_stock', 0), opening.get('stock_for_rationing_override'), today)
                    if opening.get('stock_for_requirement_override') is not None:
                        raw.execute('INSERT INTO ' + table('Importer', 'AdditionalDataStockForReqCalc')
                            + '(SKUCode,WhCode,StockForReqCalc,ReportDate) VALUES (?,?,?,?)',
                            key[0], key[1], opening['stock_for_requirement_override'], today)
                    raw.execute('INSERT INTO ' + table('Importer', 'SKULocPriorityForRationing')
                                + '(SKUCode,WhCode,Priority) VALUES (?,?,?)', key[0], key[1], policy.get('rationing_priority', 999999))
                for location in calculation['replenishment_exclusions']:
                    raw.execute('INSERT INTO ' + table('Importer', 'ExcludeReplenishment') + '(WhCode) VALUES (?)', location)
                vehicle = calculation['logistics']['vehicle']
                raw.execute('INSERT INTO ' + table('BPR', 'VehicleMaster')
                    + '(VehicleID,VehicleName,Weight,Volume) VALUES (1,?,?,?)',
                    vehicle['name'], vehicle['weight_capacity'], vehicle['volume_capacity'])
                for location in sorted({item['from_location'] for item in calculation['logistics']['items']}):
                    raw.execute('INSERT INTO ' + table('BPR', 'LocationVehicleMaster')
                                + '(LocationID,VehicleID) VALUES (?,1)', location)

                order_stages, native_stages, scripts, native_inputs = [], [], [], {}
                bpr_import, calculation_boundaries = {}, {}
                for name in r1_runner.R1_SEQUENCE:
                    if name == 'CollectDataForBPR.sql':
                        native_inputs = {name: rows('BPR', name) for name in
                            ('BPRMaster', 'DailyConsumption', 'vf_ReqCalculation', 'SKUDescriptionTbl',
                             'SiteDescriptionTbl', 'SkuLocAttributeData', 'ColorSequence', 'LastBatchRunTbl')}
                        native_inputs.update({name: rows('DBM', name) for name in ('PhaseInTbl', 'PhaseOutTbl')})
                    sql, receipt = r1_runner._read_script(name, run_timestamp=now)
                    raw.execute('USE ' + MAPPING[receipt['execution_database']])
                    runner.consume(BoundCursor(raw.cursor()).execute(sql))
                    scripts.append(receipt)
                    if name == '01. ImportData.sql':
                        bpr_import = {table_name: rows('BPR', table_name) for table_name in DAILY_PRIOR}
                    if name == 'CollectBOR_OrderAllocationData.sql':
                        calculation_boundaries['bor_oa_at_collect'] = r1_runner._capture(order_parts=True)['bor_oa']
                    if name == 'GenSupplierWiseReq.sql':
                        calculation_boundaries['supplier_bor_at_refresh'] = r1_runner._capture(order_parts=True)['supplier_bor']
                    if name in ORDER_STAGES:
                        order_stages.append((name, order_snapshot()))
                    if name in NATIVE_STAGES:
                        native_stages.append((name, native_snapshot(late=name == 'UpdateBPR.sql')))

                calculated = r1_runner._capture(order_parts=True)
                supplier_close = r1_runner._capture_supplier_state('refreshed')
                importer_close = {name: rows('Importer', name) for name in IMPORTER_PRIOR}
                controls_close = control_snapshot()
                orders_close = {name: order_stages[-1][1][name] for name in CONTRACT['tables']['orders']}
                bpr_close = {name: rows('BPR', name) for name in DAILY_PRIOR}
                dbm_before = dbm_state()
                facts = {name: deepcopy(day[name]) for name in
                         ('order_raw', 'exclusions', 'distributor_transactions', 'vendor_transactions')}
                facts.update(daily_raw=rows('Importer', 'DailyDataRaw'),
                             bpr_daily=rows('BPR', 'DailyConsumption'))
                closing = {'importer': importer_close,
                           'importer_settings': controls_close['importer_settings'],
                           'bpr': bpr_close,
                           'supplier': {'SOBData': supplier_close['refreshed_sob'],
                                        'MOQData': supplier_close['refreshed_moq']},
                           'orders': orders_close, 'controls': controls_close,
                           'dbm': dbm_before}
                full = connected.finish(prior, day, closing) if delivery else None
                snapshots = lambda values: [{'stage': name, 'state': state} for name, state in values]
                output = {
                    'MasterValidation': [{k: v for k, v in validation.items() if k != 'oracle'}],
                    'SupplierStages': [{'stage': name, **supplier[name]} for name in SUPPLIER_STAGES],
                    'DailyStages': [{'stage': name, **daily[name]} for name in daily],
                    'ControlStages': snapshots(control_stages), 'OrderStages': snapshots(order_stages),
                    'CalculationCheckpoints': calculated, 'BPRStages': snapshots(native_stages),
                    'CalculationBoundaryStages': calculation_boundaries,
                }
                result = _plain({
                    'status': 'PASS', 'output': output, 'closing': closing,
                    'dbm_before_selected': dbm_before, 'facts': facts, 'native_inputs': native_inputs,
                    'bpr_import': bpr_import,
                    'post_control_dbm_master': post_control_dbm_master,
                    'scripts': [{'name': 'ValidateAndProcessMaster.sql', 'path': str(MASTER_SCRIPT),
                                 'sha256': MASTER_SHA256, 'execution_database': 'VFTEST_Importer'},
                                import_master_receipt, *supplier_receipt['scripts'],
                                *daily_receipt['scripts'], *control_receipts, *scripts],
                })
                if delivery:
                    result['delivery'] = _plain(full)
                    result['closing'] = _plain(full['closing'])
                    result['scripts'].extend(connected.receipts)
                    result['command_inputs'] = command_receipts
                    validate_state(result['closing'])
                    if post_policy is not None:
                        # Policy selects from this SQL engine's OWN completed
                        # suggestions. It supplies no calculated values.
                        post_commands = post_policy(deepcopy(result['closing']['dbm']['Suggestions']))
                        result['post_commands'] = post_commands
                        result['post_command_receipts'] = replay_commands(raw, post_commands)
                        result['post_command_state'] = dbm_state()
        except Exception as caught:
            error = caught
        finally:
            raw.execute('IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION')
        if error is not None:
            raise error
        result['rollback_executed'] = True
        result['ownership'] = 'exclusive Fresh-only databases; counters are owned scratch'
        return result
