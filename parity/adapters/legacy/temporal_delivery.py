"""Complete selected SQL continuation inside the timeline owner's transaction.

No modern producer is called. The owner supplies an exclusive Fresh replay lease,
restricted database bindings and a rollback of its owned scratch transaction.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re

from parity.legacy_isolation import MAPPING, bind_sql

ROOT = Path('F:/VFlow_Local/local-runtime/mta-engine')
EVIDENCE = Path('F:/vflow_integrated/.local-stage7/block3-one-pass/delivery-v1')
OWNERS = {'SKULocStandardAttributes': 'Importer', 'VFSettings': 'Importer', 'ui_ReportConfigurations': 'BPR'}
AUX = {'phase_map': ('DBM', 'PhaseInPhaseOutMap'), 'phase_in_norms': ('DBM', 'PhaseInNorms'),
    'phase_exceptions': ('DBM', 'PhaseInPhaseOutExceptionLog'), 'phase_requests': ('Importer', 'PhaseOut'),
    'phase_stops': ('Importer', 'PhaseOutStop'), 'phase_in_requests': ('Importer', 'PhaseInNorms'),
    'season_status': ('DBM', 'SeasonalityStatus'), 'season_requests': ('Importer', 'Seasonality')}
PHASE = ('CollectPhaseOutData.sql', 'ProcessPhaseOut.sql', 'CollectPhaseInData.sql', 'ProcessPhaseIn.sql',
         'CollectSeasonalityData.sql', 'ProcessSeasonality.sql', 'ApplySeasonalityNormChanges.sql')


def replay_commands(raw, commands):
    """Pinned DBMProcessor writes, with the approved historical action clock.

    Called only after this engine loads its own prior DBM state and before
    current-day controls; current suggestions/norms are never supplied answers.
    """
    from datetime import datetime
    api = Path('F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll')
    digest = hashlib.sha256(api.read_bytes()).hexdigest()
    if digest != '0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346':
        raise ValueError('Selected action API drift')
    raw.execute('USE ' + MAPPING['VFTEST_DBM'])

    def plain(value):
        return value.isoformat() if hasattr(value, 'isoformat') else value

    def query(sql, parameters):
        cursor = raw.cursor()
        try:
            cursor.execute(sql, parameters)
            fields = [column[0] for column in cursor.description]
            return [{name: plain(value) for name, value in zip(fields, row)}
                    for row in cursor.fetchall()]
        finally:
            cursor.close()

    receipts = []
    for command in commands:
        selected = command['selected']
        if not selected: raise ValueError('Frozen command selection is empty')
        predicate = ' OR '.join('(SKUCode=? AND WHCode=?)' for _ in selected)
        values = tuple(v for key in selected for v in key)
        clock = datetime.fromisoformat(command['timestamp']).date().isoformat()
        matched = query(
            'SELECT S.SKUCode,S.WHCode AS WhCode,S.Type,L.OldNorm,S.NewNorm,'
            'L.SuggestionDate,R.Reason FROM Suggestions S OUTER APPLY '
            '(SELECT TOP 1 H.OldNorm,H.SuggestionDate FROM SuggestionsLog H '
            'WHERE H.SKUCode=S.SKUCode AND H.WHCode=S.WHCode AND H.Type=S.Type '
            'AND H.NewNorm=S.NewNorm ORDER BY H.SuggestionDate DESC) L '
            'LEFT JOIN ReasonCodes R ON R.Id=S.Type WHERE ' + predicate,
            values)
        expected_keys = {tuple(key) for key in selected}
        matched_keys = {(row['SKUCode'], row['WhCode']) for row in matched}
        if (matched_keys != expected_keys or len(matched) != len(expected_keys)
                or any(row['SuggestionDate'] is None or row['Reason'] is None for row in matched)):
            raise ValueError('Frozen command did not match exactly one complete prior suggestion per identity')
        if command['operation'] == 'APPLY':
            sql = ('Delete NormAcceptanceTbl From NormAcceptanceTbl A inner join '
                '(select SKUCode,WHCode from Suggestions where ' + predicate + ') b '
                'On a.SKUCode=b.SKUCode and A.WhCode=b.WhCode; Insert into NormAcceptanceTbl '
                'select A.SKUCode,A.WhCode,CONVERT(date,?),Norm,NewNorm from '
                '(select SKUCode,WHCode,NewNorm from Suggestions where ' + predicate + ') a '
                'inner join DBMMaster B on(A.SKUCode=B.SKUCode and A.WhCode=B.WhCode)')
            parameters = (*values, clock, *values)
        elif command['operation'] == 'SLEEP':
            sql = ('Insert into NormsInSleepModeTbl(SKUCode,WhCode,StartDate) '
                'select SKUCode,WHCode,CONVERT(date,?) from Suggestions with(nolock) where ' + predicate
                + '; delete from Suggestions where ' + predicate)
            parameters = (clock, *values, *values)
        else: raise ValueError('Unselected frozen command operation')
        cursor = raw.cursor()
        try:
            cursor.execute(sql, parameters)
            while cursor.nextset(): pass
        finally:
            cursor.close()
        target = 'NormAcceptanceTbl' if command['operation'] == 'APPLY' else 'NormsInSleepModeTbl'
        affected = query('SELECT * FROM ' + target + ' WHERE ' + predicate, values)
        affected_keys = {(row['SKUCode'], row['WhCode']) for row in affected}
        remaining = query('SELECT SKUCode,WHCode AS WhCode FROM Suggestions WHERE ' + predicate, values)
        if affected_keys != expected_keys or len(affected) != len(expected_keys):
            raise ValueError('Frozen command did not affect exactly one row per selected identity')
        if command['operation'] == 'SLEEP' and remaining:
            raise ValueError('Sleep command left a selected suggestion active')
        receipts.append({'command': deepcopy(command), 'api_sha256': digest,
                         'clock': 'explicit approved historical action clock; SQL DATE target',
                         'matched_before': matched, 'affected_after': affected})
    return receipts


def sequence():
    batch = (ROOT / 'Engine/RunCoreDBM.bat').read_text()
    settings = dict(re.findall(r'^set ([\w.]+)="%ROOT%\\(Scripts\\[^"\r\n]+)"', batch, re.M | re.I))
    ingestion = ('DBM/DailyDataImportExport/02. GetDailyData.sql', 'DBM/DailyDataImportExport/ImportExclusions.sql',
                 'DBM/DailyDataImportExport/ImportOrderData.sql', 'DBM/CalculateExtendedOCP.sql')
    items = [('ingestion', 'DBM', 'Scripts/' + p, {}) for p in ingestion]
    tokens = re.findall(r'^%CMDSTR% %(PRE\d+|SUSP[\d.]+|POST\d+)%', batch[:batch.index('rem *** DBM rules')], re.M)
    # POST1/2 are reassigned later by the BAT; suspension bindings are captured
    # at their actual point in execution, before those assignments.
    early = dict(re.findall(r'^set ([\w.]+)="%ROOT%\\(Scripts\\[^"\r\n]+)"', batch[:batch.index('rem *** DBM rules')], re.M | re.I))
    items += [('suspension', 'DBM', early[k].replace('\\', '/'), {}) for k in tokens]
    items += [('rule', 'DBM', settings['RULE' + str(i)].replace('\\', '/'), {}) for i in (*range(1, 7), 12)]
    items += [
        ('discard', 'DBM', 'Scripts/DBM/SuspensionRules/DiscardSuggestions.sql', {}),
        ('reports', 'DBM', 'Scripts/DBM/DBMRules/08. GenerateReports.sql', {}),
        ('order-summary', 'DBM', 'Scripts/DBM/Misc/UpdateOrderSummaryData.sql', {}),
        ('norm1-advisory', 'DBM', 'Scripts/DBM/AdditionalRules/Norm1IncreaseSuggestions.sql', {}),
        ('norm-change-export', 'DBM', 'Scripts/DBM/DBMNormChange/ExportDBMNormChange.sql', {'DBMNormChangeReportHorizon': '1'}),
        ('suspension-history', 'DBM', 'Scripts/DBM/SuspensionRules/GatherSuspensionHistory.sql', {}),
        ('norm-change-history', 'DBM', 'Scripts/DBM/NormChangeHistory.sql', {'NormChangeLogHorizon': '7'}),
    ]
    for norm in (0, 1, 2):
        for stage, name in (('data', f'Norm{norm}Data.sql'), ('detail', 'GenerateNorm0-1-2Report.sql'),
                            ('export', 'ExportNorm0-1-2Report.sql'), ('clear', 'ClearNorm0-1-2ReportData.sql')):
            items.append((f'norm{norm}-{stage}', 'DBM', 'Scripts/DBM/Norm 0-1-2 Reports/' + name,
                          {'Horizon': '30', 'ReportName': 'Norm_0_1_2Report'}))
    items.append(('daily-cleanup', 'DBM', 'Scripts/DBM/ClearHistoryData_DBM.sql', {'DailyConsumptionHorizonDBM': '370'}))
    contract = json.loads((EVIDENCE / 'btr-source-contract.json').read_text())
    items += [(Path(r['path']).name, 'BTR', r['path'], {}) for r in contract['sources'] if r['path'].startswith('Scripts/')]
    return items


def prepare():
    # Read-only retained metadata. Never create or bless source pins on replay.
    register=json.loads((Path(__file__).resolve().parents[3]/'baseline/temporal-oracle-reuse.json').read_text())
    for resource in register['resources']:
        if hashlib.sha256(Path(resource['path']).read_bytes()).hexdigest()!=resource['sha256']:
            raise ValueError('Registered oracle metadata differs: '+resource['path'])
    baseline=json.loads((Path(__file__).resolve().parents[3]/'baseline/manifest.json').read_text())
    for row in baseline['canonical_api']+baseline['engine_sources']:
        if hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Canonical source changed: '+row['path'])
    pins=json.loads((EVIDENCE/'full-sql-pins.json').read_text())
    for path,expected in pins.items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:
            raise ValueError('Pinned SQL source drift: '+path)
    return pins


class DeliverySQL:
    def __init__(self, raw, load, rows, dbm_state, scratch_state, pins, today, profile):
        self.raw, self.load, self.rows = raw, load, rows
        self.dbm_state, self.scratch_state, self.pins = dbm_state, scratch_state, pins
        self.today, self.profile = today, profile
        self.receipts = []
        self.exported = {}
        self.diagnostics = {}

    def execute(self, role, path, extra=None):
        raw = (ROOT / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != self.pins[path]: raise ValueError('SQL source changed after pin')
        maintenance = None
        if path == 'Scripts/DBM/SuspensionRules/03.1 AcceptedNormsStockType.sql':
            from parity.adapters.legacy.temporal_maintenance import source_receipt, MAINTENANCE
            maintenance = source_receipt()['maintenance_capture']
            raw = raw.replace(MAINTENANCE, b'-- Approved capture-only omission: shared tempdb maintenance is outside rollback')
        encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'cp1252'
        sql = raw.decode(encoding)
        variables = {r + 'Database': d for r, d in ((k[7:], v) for k, v in MAPPING.items())}
        variables.update(ImporterDB=MAPPING['VFTEST_Importer'], DBMDataBase=MAPPING['VFTEST_DBM'],
            DBMDB=MAPPING['VFTEST_DBM'], BufferTrendDatabase=MAPPING['VFTEST_BTR'],
            ScriptExecutionFlagQuery='UPDATE ' + MAPPING['VFTEST_Importer'] + '.dbo.ScriptExecutedFlag SET IsScriptExecuted=1 WHERE ScriptName=',
            RunDate=self.today, RunDateTime=self.today + 'T00:00:00', PI_PO_FromUI='1', FNCFromUI='1',
            CARNoColorToleranceDuration='2', **(extra or {}))
        for key, value in variables.items(): sql = sql.replace('$(' + key + ')', str(value))
        if re.search(r'\$\(', sql): raise ValueError('Unbound SQL variables in ' + path + ': ' + str(re.findall(r'\$\(([^)]+)\)', sql)))
        sql = bind_sql(sql)
        self.raw.execute('USE ' + MAPPING['VFTEST_' + role])
        sets = []
        for batch in re.split(r'^\s*GO\s*$', sql, flags=re.M | re.I):
            if not batch.strip(): continue
            # Each production sqlcmd invocation has its own local-temp scope.
            # A nested batch reproduces that scope while retaining the owner's
            # exclusive connection/transaction; otherwise stale #tbl_1 schemas
            # from earlier scripts can break compilation before DROP executes.
            cursor = self.raw.cursor()
            try:
                cursor.execute('EXEC sys.sp_executesql ?', batch)
                failure = None
                while True:
                    if cursor.description:
                        labels = [d[0] for d in cursor.description]
                        fields = [label if label and labels.count(label) == 1 else '__column_' + str(i)
                                  for i, label in enumerate(labels)]
                        records = [dict(zip(fields, r)) for r in cursor.fetchall()]
                        if any(f.lower() in ('error', 'errornumber', 'errormessage') for f in fields):
                            failure = records
                        sets.append(records)
                    if not cursor.nextset(): break
                if failure is not None: raise ValueError(str(failure))
            except Exception as error:
                raise RuntimeError('Canonical SQL execution failed in ' + path + ': ' + str(error)) from error
            finally:
                cursor.close()
        self.receipts.append({'path': path, 'sha256': self.pins[path], 'role': role,
                              **({'maintenance_capture': maintenance} if maintenance else {})})
        return sets

    def report(self, name, fields):
        from parity.adapters.legacy.r1_runner import R1_FORCE_SCRIPTS
        path, _, role = R1_FORCE_SCRIPTS[name]
        sets = self.execute(role[7:], 'Scripts/' + path)
        if len(sets) != 2 or len(sets[0]) != 1 or list(sets[0][0].values()) != list(fields):
            raise ValueError('Unexpected diagnostic report header: ' + name)
        return [{('WhCode' if k == 'WHCode' else k): v for k, v in zip(fields, row.values())}
                for row in sets[1]]

    def after_control(self, name):
        if name == 'UpdateNormChanges.sql':
            self.execute('DBM', 'Scripts/DBM/Misc/CollectFailedForceNormData.sql')
            self.diagnostics['failed_force'] = self.report('FailedForceNormChange.sql',
                ('SKUCode', 'WHCode', 'VectorFlowNorm', 'Reason'))

    def aux(self):
        return {k: self.rows(*binding) for k, binding in AUX.items()}

    def controls(self, prior, day, snapshot):
        from parity.adapters.legacy.r1_runner import R1_FORCE_SCRIPTS
        for name, binding in AUX.items():
            self.load(*binding, prior['control_aux'][name])
            if name in day['control_requests']:
                self.load(*binding, day['control_requests'][name], append=True)
        stages = []
        for name in PHASE:
            path, _, role = R1_FORCE_SCRIPTS[name]
            self.execute(role[7:], 'Scripts/' + path)
            if name == 'ProcessPhaseIn.sql':
                self.diagnostics['phase_exceptions'] = self.report('GeneratePhaseInPhaseOutExceptionReport.sql',
                    ('PhaseOutSKUCode', 'WhCode', 'PhaseInSKUCode', 'TargetNorm', 'Reason', 'Date'))
            stages.append((name, {**snapshot(), **self.aux()}))
        return stages

    def finish_controls(self, snapshot):
        from parity.adapters.legacy.r1_runner import R1_FORCE_SCRIPTS
        for name in ('ClearPhaseInPhaseOutData.sql',):
            path, _, role = R1_FORCE_SCRIPTS[name]
            self.execute(role[7:], 'Scripts/' + path)
        self.control_aux = self.aux()
        self.control_close = {**snapshot(), **self.control_aux}
        return ('ClearPhaseInPhaseOutData.sql', self.control_close)

    def finish(self, prior, day, closing):
        for name, role, source in (('order_raw', 'Importer', 'OrderDataRaw'), ('exclusions', 'Importer', 'Exclusions'),
                                  ('distributor_transactions', 'Distributor', 'TransactionLog'), ('vendor_transactions', 'Vendor', 'TransactionLog')):
            self.load(role, source, day[name])
        btr_contract = json.loads((EVIDENCE / 'btr-source-contract.json').read_text())
        # Only these six populations are BTR's source opening. The remaining
        # closing-envelope tables are regenerated below; in particular BPR
        # ExpediteDispatches is computed from this day's Pick, and Importer
        # standard attributes already belong to the current DBM state.
        for name in btr_contract['required_prior_tables']:
            self.load('BTR', name, prior['btr'][name])
        # SetRunDate.bat explicitly writes the external business date to BTR.
        # This is a clock input, never a prepared current-day calculation.
        self.load('BTR', 'LastBatchRunTbl', [{'LastRunDate': self.today + 'T00:00:00'}])
        for name, values in prior['consumer_context'].items():
            role = {'CWH_List': 'BPR', 'CategoryColDescription': 'BTR', 'DistributorList': 'Distributor',
                    'GoodsInTransitTransporterMaster': 'BPR', 'NMSAllItems': 'Importer'}[name]
            self.load(role, name, values)
        settings = self.rows('Importer', 'VFSettings')
        retained_settings = json.loads((EVIDENCE / 'consumer-settings-full.json').read_text())
        for name, value in self.profile['delivery']['btr_settings'].items():
            if name == 'CARNoColorToleranceDuration': continue
            matching = [r for r in retained_settings if r['Parameter'] == name]
            if len(matching) != 1 or str(matching[0]['Value']) != str(value):
                raise ValueError('Retained BTR setting drift: ' + name)
            settings = [r for r in settings if r['Parameter'] != name] + matching
        self.load('Importer', 'VFSettings', settings)
        # Canonical snapshot is disabled by NMSActive0; its existing history is
        # preserved. The current expedite membership comes from actual Pick.
        self.execute('Importer', 'Scripts/Importer/NMSCreateSnapshot.sql')
        self.execute('BPR', 'Scripts/BPR/CollectDataToExpediteDispatches.sql')
        stages, boundaries, reports = [], {}, []
        items = sequence()
        for i, (stage, role, path, extra) in enumerate(items):
            sets = self.execute(role, path, extra)
            if role == 'BTR': continue
            if stage in ('norm-change-export', 'norm-change-history') or stage.endswith('-export'):
                if len(sets) != 2: raise ValueError('Report must return header and complete rows: ' + stage)
                self.exported = dict(ReportHeader=[{'values': list(r.values())} for r in sets[0]],
                                     ReportRows=[{'values': list(r.values())} for r in sets[1]])
            state = {**self.dbm_state(), **deepcopy(self.exported)}
            stages.append((stage, state))
            next_stage = items[i + 1][0] if i + 1 < len(items) else None
            if stage == 'ingestion' and next_stage != stage: boundaries['dbm-imported'] = state
            if stage == 'suspension' and next_stage != stage: boundaries['final-suspensions'] = state
            if stage == 'discard': boundaries['final-suggestions'] = state
            if stage == 'daily-cleanup': boundaries['post-rule-reports'] = state
            if stage in ('norm-change-export', 'norm-change-history', 'norm1-advisory') or stage.startswith(('norm0-', 'norm1-', 'norm2-')):
                reports.append({'stage': stage, 'tables': {n: state[n] for n in ('ReportHeader', 'ReportRows',
                    'Norm0Norm1Norm2Report', 'Norm0_1_2ReportDetails', 'Norm1IncreaseSuggestions') if n in state}})
        btr_contract = json.loads((EVIDENCE / 'btr-source-contract.json').read_text())
        names = set(btr_contract['required_prior_tables']) | set(btr_contract['generated_table_fields']) | {'LastBatchRunTbl'}
        btr = {n: self.rows('BTR', n) for n in sorted(names)}
        btr['SKULocStandardAttributes'] = self.rows('Importer', 'SKULocStandardAttributes')
        btr['ExpediteDispatches'] = [{n: r[n] for n in ('SKUCode', 'WhCode', 'BRAge', 'BRAgeRedCount', 'BRAgeBlackCount')}
                                    for r in self.rows('BPR', 'ExpediteDispatches')]
        dbm = self.dbm_state()
        # Only the originally declared DBM VFSettings subset belongs to this
        # DBM envelope; the independently configured BTR settings are profile.
        dbm['VFSettings'] = [r for r in dbm['VFSettings'] if r['Parameter'] in {v['Parameter'] for v in prior['dbm']['VFSettings']}]
        closing.update(dbm=dbm, btr=btr, control_aux=self.control_aux,
                       consumer_context=deepcopy(prior['consumer_context']), publication_context=deepcopy(prior['publication_context']))
        from parity.adapters.legacy.temporal_support import SHARED_CONTROLS
        for name, source in SHARED_CONTROLS.items():
            closing['controls'][name] = [{('WhCode' if k == 'WHCode' else k): v for k, v in r.items()} for r in dbm[source]]
        boundaries.update({'btr-insights': btr, 'closing-state': closing})
        boundaries['controls'] = {'controls': self.control_close, 'diagnostics': self.diagnostics}
        return {'stages': stages, 'reports': reports, 'boundaries': boundaries, 'closing': closing}
