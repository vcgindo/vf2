"""Mapped O7 files and all fourteen durable local evaluations; never sends mail."""
import json
from pathlib import Path
from mta.application.operational_alerts import ALERT_SEEDS, evaluate_alert
from mta.application.operational_alert_files import (
    invalid_data_bytes, phase_exception_bytes, failed_force_bytes, unavailable_daily_bytes)
from mta.application.operational_report_files import (
    invalid_data_report_files, phase_exception_report_files, failed_force_report_files,
    unavailable_daily_report_files)
from mta.runtime.operational_alert_sources import read_alert_inputs
from mta.runtime.operational_attempts import configuration_value, _identity
from mta.runtime.operational_effects import operation, record_intent
from mta.runtime.operational_models import OperationalAttempt
from mta.runtime.operational_native import save_population
from mta.runtime.operational_reports import _record_final_files
from mta.runtime.operational_repair import resolve_operational_file
from mta.serialization import digest


def source_pins():
    manifest = json.loads((Path(__file__).resolve().parents[2]/'baseline/manifest.json').read_text())
    registered = {row['path'].replace('\\', '/').lower(): row['sha256'] for row in manifest['engine_sources']}
    names = sorted({value for seed in ALERT_SEEDS for value in (seed['wrapper'], seed['sql'])})
    result = {}
    for name in names:
        matches = [value for path, value in registered.items() if path.endswith('/'+name.lower())]
        if len(matches) != 1:
            raise ValueError('Canonical alert source pin absent or ambiguous: '+name)
        result[name] = matches[0]
    return result


ALERT_OPERATION = dict(name='GenericLocalAlerts', stage='source-positioned-alerts',
                       source_digest=digest(source_pins()))
DISPOSITIONS = dict(READY='LOCAL_READY', DISABLED_SETTING='DISABLED',
    DISABLED_OPERATION='DISABLED', PREDICATE_FALSE='PREDICATE_FALSE',
    RECIPIENT_SUPPRESSED='RECIPIENT_SUPPRESSED', UNAVAILABLE='ATTACHMENT_UNAVAILABLE')


def artifact_facts(owner):
    """Existing producer receipts, including the parent report's deleted CSV size."""
    facts, receipts = {}, {}
    files = [file for effect in owner.operations.order_by('ordinal') for file in effect.files.order_by('id')]
    for file in files:
        name = Path(file.relative_path).name
        if name in facts and not file.relative_path.startswith('output/'):
            continue
        actual = resolve_operational_file(file)
        members = list(actual.members.order_by('ordinal').values('name', 'size_bytes'))
        facts[name] = dict(available=True, byte_size=actual.size_bytes,
                           members=[member['name'] for member in members])
        receipts[name] = dict(relative_path=file.relative_path, sha256=actual.sha256, size_bytes=actual.size_bytes)
        if name == 'NoNormParentReport.zip':
            if [member['name'] for member in members] != ['NoNormParentReport.csv']:
                raise ValueError('Parent report native member is unavailable')
            facts['NoNormParentReport.csv'] = dict(available=True, members=[], byte_size=members[0]['size_bytes'])
    return facts, receipts


def materialize_alert_operation(attempt_id, *, archive_writer):
    owner = OperationalAttempt.objects.select_related('run', 'configuration').get(pk=attempt_id)
    config = configuration_value(owner.configuration)
    current = _identity(owner.run)
    if any(current[key] != getattr(owner, 'run_output_digest' if key == 'output_digest' else key)
           for key in current):
        raise ValueError('Alert source/action identity drift')
    roster = [row for row in config['bindings'].get('operation_roster', []) if row.get('group') == 'O7']
    if len(roster) != 1 or {key: roster[0].get(key) for key in ALERT_OPERATION} != ALERT_OPERATION:
        raise ValueError('Canonical alert operation roster differs')
    inputs = read_alert_inputs(owner)
    populations, settings = inputs['populations'], inputs['settings']
    alert_config, reports = inputs['configuration'], inputs['reports']
    clock = alert_config['run_datetime']
    with operation(owner, **roster[0]) as effect:
        save_population(owner, 'closing/RunAbortReasons', 'Importer/RunAbortReasons', populations['RunAbortReasons'])
        write_alert_files(effect, inputs, archive_writer=archive_writer)
        facts, attachments = artifact_facts(owner)
        source = digest(dict(owner=owner.source_digest, native=source_pins(), inputs=inputs))
        unavailable = []
        for seed in ALERT_SEEDS:
            result = evaluate_alert(seed['name'], settings=settings, configuration=alert_config,
                                    populations=populations, artifacts=facts)
            attachment = result['attachment']
            bound = []
            if attachment and attachment['available']:
                bound = [attachments[attachment['name']]]
            record_intent(effect, alert_name=result['alert_name'], branch=result['branch'], stage=result['stage'],
                source_digest=source, recipients=result['recipient'], subject=result['subject'], body=result['body'],
                disposition=DISPOSITIONS[result['status']], reason=result['reason'], attachments=bound)
            if result['status'] == 'UNAVAILABLE':
                unavailable.append(seed['name'])
        if unavailable:
            raise ValueError('Required native alert attachment unavailable: '+', '.join(unavailable))
    return effect


def write_alert_files(effect, inputs, *, archive_writer):
    """Shared mapped file producer for ordinary execution and linked repair."""
    owner = effect.attempt
    populations, reports = inputs['populations'], inputs['reports']
    config = inputs['configuration']
    clock = config['run_datetime']
    receipts = [invalid_data_report_files(root=owner.root,
        report_bytes=invalid_data_bytes(populations['RejectedMaster'], clock),
        attach_zip=config['attach_invalid_data_report_zip'], archive_writer=archive_writer)]
    receipts.append(failed_force_report_files(root=owner.root, business_date=owner.business_date.isoformat(),
        report_bytes=failed_force_bytes(reports['failed_force'])))
    count = len(reports['phase_exceptions'])
    receipts.append(phase_exception_report_files(root=owner.root, exception_count=count,
        report_bytes=phase_exception_bytes(reports['phase_exceptions']) if count else None,
        archive_writer=archive_writer))
    if not config['critical_data_available']:
        receipts.append(unavailable_daily_report_files(root=owner.root,
            report_bytes=unavailable_daily_bytes(populations['RunAbortReasons'], clock), archive_writer=archive_writer))
    for receipt in receipts:
        _record_final_files(effect, receipt)
