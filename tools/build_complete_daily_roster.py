"""Build the finite source/configuration contract; never execute a daily engine.

This is a contract map, not an execution tracker. Missing configuration remains
unresolved. A caller cannot obtain a runnable contract from schema emptiness or
from an enabled group alone: concrete operation/output qualification is separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.assess_daily_coverage import frozen_configuration


ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path('F:/VFlow_Local/local-runtime/mta-engine')
FROZEN = Path('D:/freshvcf-build/synthetic/rlt-4-7-v1/scenario-004/full-input.json')
FROZEN_SHA = 'ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56'

# Ordered producer groups from the already reconciled complete-day map. A group
# does not certify its child SQL calls; critical writers are inventoried below.
# activation: required, configured, data-dependent, or explicitly disabled.
GROUPS = (
    ('settings', 'Engine/VectorFLOWv4.bat', 'required', ['C1'], ['effective configuration']),
    ('fullkit', 'Engine/CheckRunStartCriteria.bat', 'required', ['C1', 'C3'], ['FullkitAvailable', 'FullkitCheckdate', 'CriticalFiles']),
    ('sanitation', 'Engine/DataSanitizationUtility.bat', 'required', ['C1'], ['DataSanitizationResult gate']),
    ('pre-backup', 'Engine/Backup.bat', 'disabled:IsPreBackupActive=0', [], []),
    ('reset', 'Scripts/Importer/ResetBatchExecutionFlag.sql', 'required', ['C1'], ['ScriptExecutedFlag', 'ImporterSettingsTbl']),
    ('site-pre', 'Engine/SiteSpecific/GulfOil/PreProcessing.bat', 'required', ['C1'], ['site pre-processing effects']),
    ('run-date', 'Engine/SetRunDate.bat', 'required', [], ['all LastBatchRunTbl owners']),
    ('raw-input', 'Engine/ImportAllRawData.bat', 'required', ['C3'], ['raw master/daily/supplier/control rows']),
    ('vendor', 'Engine/ImportVendorData.bat', 'disabled:VendorSystemActive=0', [], []),
    ('distributor', 'Engine/ImportDistributorData.bat', 'disabled:DistributorSystemActive=0', [], []),
    ('input-validation', 'Engine/ValidateAndProcessInputData.bat', 'required', [], ['processed/rejected input rows', 'validation reports']),
    ('norm-controls', 'Engine/NormChangesRun.bat', 'required', [], ['effective Norms', 'control histories', 'cleared requests']),
    ('parent-norm', 'Engine/ValidateParentNorm.bat', 'required', ['C3', 'C4'], ['NoNormParent report', 'conditional CSV/ZIP/alert intent']),
    ('task-status', 'Scripts/Importer/NMSTaskStatusUpdate.sql', 'required', [], ['NMS task status and retention']),
    ('runtime-post-importer', 'Engine/GenerateRuntimeReports.bat', 'configured:PostImporter', ['C1', 'C3'], ['configured resultsets/files']),
    ('bpr-core', 'Engine/RunCoreBPR.bat', 'required', [], ['requirements/ration/Pick/BPR/supplier rows']),
    ('pick-files', 'Engine/PickListReports.bat', 'required', ['C3'], ['four Pick report files']),
    ('order-allocation-files', 'Engine/OrderAllocBasedReports.bat', 'configured:IsMTOEnvironment=0', ['C3'], ['BOR_OrderAllocation.csv', 'BOR and RRR allocation histories; MTO files disabled']),
    ('bpr-exception-files', 'Engine/GenerateBPRExceptionReport.bat', 'data-dependent:BPRExceptions nonempty', ['C3', 'C4'], ['BPR exception CSV/ZIP presence and alert intent']),
    ('production-orders', 'Scripts/BPR/ProdOrderSuggestions.sql', 'required', [], ['ProdOrderSuggestions', 'cleared Intermediate tables']),
    ('bpr-retention', 'Scripts/BPR/ClearHistoryData_BPR.sql', 'required', [], ['DailyConsumption', 'BPR/request/transit remark retention']),
    ('modified-rrr', 'Engine/RunCoreBPR.bat', 'disabled:GenerateModifiedRRR=0', [], []),
    ('planning', 'Engine/Planning.bat', 'required', [], ['GIT/excess/expedite/order fulfillment final populations']),
    ('bpr-completion', 'Scripts/BPR/ValidateBPRBatchExecutionFlags.sql', 'required', ['C1', 'C6'], ['IsBPRBatchFileExecuted']),
    ('bpr-failure-clear', 'Scripts/BPR/ClearTableForBPRBatchExecutionFailure.sql', 'data-dependent:BPR completion failed', ['C6'], ['four cleared legacy report tables; failed modern candidate denied']),
    ('post-bpr', 'Scripts/SiteSpecific/GulfOil/BPR/CalculatedAttributes.sql', 'required', ['C1'], ['BPR/Importer/NMS c3', 'cleared Intermediate tables']),
    ('runtime-post-bpr', 'Engine/GenerateRuntimeReports.bat', 'configured:PostBPR', ['C1', 'C3'], ['configured resultsets/files']),
    ('input-download', 'Engine/ProvideInputDataForDownload.bat', 'configured:GenerateDownloadableInputData=1', ['C3'], ['InputData.zip and members', 'input date file']),
    ('dbm-pre', 'Engine/SiteSpecific/GulfOil/PreDBMProcessing.bat', 'required', ['C1'], ['site pre-DBM effects']),
    ('dbm-core', 'Engine/RunCoreDBM.bat', 'required', [], ['DBM imported/rules/suspensions/suggestions and histories', 'configured resultsets']),
    ('dbm-files', 'Engine/RunCoreDBM.bat', 'configured:frozen Norm/phase-out report settings', ['C3', 'C4'], ['DBMNormChange and configured Norm0/1/2 and phase-out files', 'alert intents']),
    ('post-dbm', 'Engine/SiteSpecific/GulfOil/PostDBMProcessing.bat', 'required:no business commands in retained hook', ['C1'], []),
    ('runtime-post-dbm', 'Engine/GenerateRuntimeReports.bat', 'configured:PostDBM', ['C1', 'C3'], ['configured resultsets/files']),
    ('btr-core', 'Engine/RunCoreBufferTrend.bat', 'required', [], ['BTR history/trends/core attributes; standard 30/60/90 and location files disabled']),
    ('post-btr-attributes', 'Scripts/SiteSpecific/GulfOil/BTR/CalculateAttributeBasedonBTR.sql', 'required', ['C1', 'C2'], ['FGTrendData', 'c9/c10/c12/c13 in six owners', 'cleared Intermediate tables']),
    ('post-btr-files', 'Scripts/SiteSpecific/GulfOil/BTR/GulfOil_BTRReports.py', 'required', ['C1', 'C3'], ['GulfOil BTR Python reports']),
    ('runtime-post-btr', 'Engine/GenerateRuntimeReports.bat', 'configured:PostBTR', ['C1', 'C3'], ['configured resultsets/files']),
    ('ui-upload-logs', 'Engine/GenerateUIUploadLogs.bat', 'configured:ActivateNMSUIUploadLogs=1', ['C3'], ['UI upload log files and retention']),
    ('batch-completion', 'Scripts/Importer/ValidateBatchExecutionFlags.sql', 'required', ['C1', 'C6'], ['IsBatchFileExecuted']),
    ('site-final', 'Engine/SiteSpecific/GulfOil/FinalProcessing.bat', 'required:no business commands in retained hook', ['C1'], []),
    ('runtime-final', 'Engine/GenerateRuntimeReports.bat', 'configured:Final', ['C1', 'C3'], ['configured resultsets/files']),
    ('post-backup', 'Engine/Backup.bat', 'configured:DoPostBkpDBM/BPR/Importer/BTR=1', ['C3', 'C5'], ['four native SQL differential backups and compressed files', 'modern native backup']),
    ('alerts', 'Engine/VectorFLOWv4.bat', 'configured:seeded EmailAlertSettings plus data predicates', ['C1', 'C4'], ['evaluated alert intents/attachments']),
    ('actions', 'Engine/VectorFLOWv4.bat', 'approved:frozen eligible-Sleep/Apply policy', [], ['ordered real workflow commands', 'own successor state']),
    ('publication-readers', 'Engine/VectorFLOWv4.bat', 'readiness:explicit supported operational policy; strict existing defaults preserved', ['C1', 'C2', 'C3', 'C4', 'C5', 'C6'], ['typed final roots', 'prepared layers/seals/access', 'explicit owned selection', 'finite serialized reader responses']),
)

SETTING_NAMES = frozenset(('DoPostBkpDBM', 'DoPostBkpBPR', 'DoPostBkpImporter',
    'DoPostBkpBTR', 'Zip', 'DBBkpCompress', 'GenerateLocWiseBTR', 'BTR30Days',
    'BTR60Days', 'BTR90Days', 'AutoDBMActive', 'OrchestratorImplemented',
    'DailyConsumptionHorizonBPR', 'BPR_RemarkHorizon', 'GenerateModifiedRRR',
    'ActivateNorm0Report30Days', 'BPR_ShowNormZeroItems'))


def identity(path):
    raw = path.read_bytes()
    return {'path': path.as_posix(), 'sha256': hashlib.sha256(raw).hexdigest()}


def seed_rows(text, table, columns):
    """Parse only the literal INSERT grammar used by these two pinned seed sets."""
    prefix = 'INSERT [dbo].[' + table + '] '
    rows = []
    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        match = re.fullmatch(re.escape(prefix) + r'\((.*?)\) VALUES \((.*?)\);?', line)
        if not match:
            raise ValueError('Unrecognized seed INSERT: ' + table)
        actual = re.findall(r'\[([^]]+)\]', match[1])
        if actual != list(columns):
            raise ValueError('Seed columns changed: ' + table)
        tokens = re.findall(r"N'(?:''|[^'])*'|NULL|-?\d+", match[2])
        if ', '.join(tokens) != match[2] or len(tokens) != len(columns):
            raise ValueError('Nonliteral seed values: ' + table)
        values = [t[2:-1].replace("''", "'") if t.startswith("N'") else
                  None if t == 'NULL' else int(t) for t in tokens]
        rows.append(dict(zip(columns, values)))
    return rows


def build():
    if identity(FROZEN)['sha256'] != FROZEN_SHA:
        raise ValueError('Frozen facts changed')
    manifest = json.loads((ROOT/'baseline/manifest.json').read_text(encoding='utf-8'))
    pins = {Path(r['path']).as_posix().lower(): r['sha256'] for r in manifest['engine_sources']}
    sources = {}

    def source(relative, *, unregistered=False):
        if relative in sources:
            return relative
        path = ENGINE/relative
        item = identity(path)
        pin = pins.get(path.as_posix().lower())
        if pin is None and not unregistered:
            raise ValueError('Canonical source not registered: ' + relative)
        if pin is not None and pin != item['sha256']:
            raise ValueError('Canonical source changed: ' + relative)
        item['baseline_registered'] = pin is not None
        sources[relative] = item
        return relative

    importer = source('Scripts/DBCreation/Importer_DBCreation.sql')
    bpr = source('Scripts/DBCreation/BPR_DBCreation.sql')
    text = (ENGINE/importer).read_text(encoding='utf-8-sig')
    flags = seed_rows(text, 'ScriptExecutedFlag',
                      ('ScriptName', 'IsScriptExecuted', 'IsScriptCritical', 'ModuleName'))
    alerts = seed_rows(text, 'EmailAlertSettings', ('AlertName', 'IsActive'))
    if len(flags) != 206 or len(alerts) != 14:
        raise ValueError('Seed roster differs from retained reconciliation')
    settings = []
    for relative in ('Engine/StdSettingsPre.bat', 'Engine/SiteSpecific/GulfOil/Settings.bat'):
        source(relative)
        for number, line in enumerate((ENGINE/relative).read_text(encoding='utf-8-sig').splitlines(), 1):
            match = re.match(r'\s*set\s+(\w+)=(.*?)\s*$', line, re.I)
            if match and match[1] in SETTING_NAMES:
                settings.append({'source': relative, 'line': number,
                                 'name': match[1], 'value': match[2]})
    operations = []
    for ordinal, (name, relative, activation, dependencies, outputs) in enumerate(GROUPS):
        source(relative, unregistered=relative.endswith('GulfOil_BTRReports.py'))
        operations.append(dict(ordinal=ordinal, id=name, source=relative,
            activation=activation, configuration_dependencies=dependencies,
            output_obligations=outputs))
    # Literal flag markers are retained, not repaired to match filename spelling.
    # Not every script containing a marker is actually reachable in this workload.
    markers = {}
    for row in manifest['engine_sources']:
        if not row['path'].lower().endswith('.sql'):
            continue
        path = Path(row['path'])
        if not path.is_relative_to(ENGINE):
            continue
        # Flag labels are ASCII. Decode bytes losslessly for this lexical scan;
        # deployed files include both UTF-8 and Windows-1252 comment text.
        sql = path.read_bytes().decode('latin-1')
        found = re.findall(r"concat\('\$\(ScriptExecutionFlagQuery\)',\s*'''([^']+)'''\)", sql, re.I)
        if found:
            observed = identity(path)
            if observed['sha256'] != row['sha256']:
                raise ValueError('Critical writer source changed: ' + path.as_posix())
            for flag in found:
                markers.setdefault(flag, []).append(observed)
    critical = [dict(row, candidate_literal_writers=markers.get(row['ScriptName'], []))
                for row in flags if row['IsScriptCritical'] == 1]
    case = json.loads(FROZEN.read_text(encoding='utf-8'))['case']
    return dict(schema='fresh-complete-daily-operation-roster-v1',
        status_tracker='docs/MIGRATION.md', executable=False,
        qualification='Finite producer/configuration contract only. C1-C6 approved; concrete operation qualification and main-flow integration remain required. Benchmark execution held; this map grants no business-day execution.',
        frozen_input=identity(FROZEN), business_dates=['2026-06-06', '2026-06-07'],
        benchmark_execution='HELD by human scope change; new real business-day correctness execution requires specific approval',
        historical_invocation_limits={'production_per_engine': 2, 'conditional_validation_per_engine': 2,
                           'total_per_engine': 4, 'warmups': 0, 'retries': 0},
        unresolved_configuration=[],
        approved_configuration=dict(
            ids=['C1', 'C2', 'C3', 'C4', 'C5', 'C6'],
            question_id='call_bcfe99ea9c2d40af8c9de82ff0f529bc',
            answer='Approve C1–C6 as documented',
            package=identity(ROOT/'docs/COMPLETE_DAILY_CONFIGURATION_DECISIONS.md')),
        configuration_decisions='docs/COMPLETE_DAILY_CONFIGURATION_DECISIONS.md',
        frozen_configuration=frozen_configuration(case), static_settings=settings,
        schema_seed_candidates={'source': importer, 'ScriptExecutedFlag': flags,
                                'EmailAlertSettings': alerts},
        schema_only_candidates={'RuntimeReports': bpr, 'CriticalFiles': importer,
                                'DataSanitizationResult': importer},
        critical_script_candidates=critical, operations=operations, sources=sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build()
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'operations': len(result['operations']),
        'critical_scripts': len(result['critical_script_candidates']),
        'unresolved_configuration': result['unresolved_configuration'],
        'executable': False, 'output': str(args.output)}))


if __name__ == '__main__':
    main()
