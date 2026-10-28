"""Native-image operator adapter for CSV scope validation; reuse existing owners.

No calculation, admission, hook or report algorithm is implemented here. This
path preserves old test contracts and explicitly selected generic policies.
"""
import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import urllib.request

SCOPES = ('Full', 'UptoBPR', 'PostBPR', 'UptoDBM', 'PostDBM')
TAILS = {'PostBPR': 'UptoBPR', 'PostDBM': 'UptoDBM'}
LIMIT = 1024 * 1024
ROOT = Path('/var/lib/vectorflow/csv-scopes')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def read_json(path):
    from mta.application.production_csv_files import decode_json
    with Path(path).open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Scope metadata exceeds its bound')
    return decode_json(raw)


def operation_record(root):
    path = root / 'operation.json'
    if path.exists():
        return read_json(path)
    if root.exists():
        raise ValueError('Incomplete frozen scope directory has no operation receipt; preserve it and diagnose before stop')
    return None


def profile_reference(profile, initialization_id, source_digest, *, policy_mode='retained-test', site_code=None):
    """Rebind supplied configuration to THIS opening; never adopt an old run."""
    from mta.application import runtime_report_configuration as definitions
    from mta.runtime import runtime_report_request as request
    from mta.serialization import digest
    production_profile = isinstance(profile, dict) and profile.get('schema') == 'vectorflow-production-scope-profile-v1'
    if production_profile:
        from mta.runtime.production_scope_policy import GENERIC_POLICY
        if (policy_mode != 'generic' or set(profile) != {
                'schema', 'configuration', 'business_policy', 'client_processing', 'authority'}
                or profile['business_policy'] != GENERIC_POLICY or profile['client_processing'] is not False):
            raise ValueError('Explicit generic production profile without client processing required')
    elif (type(profile) is not dict or set(profile) != {
            'schema', 'configuration', 'hook', 'disposition', 'authority'}
            or profile['schema'] != 'vectorflow-scope-validation-profile-v1'
            or type(profile['authority']) is not str or not profile['authority'].strip()):
        raise ValueError('Explicit offline scope validation profile required')
    if type(profile['authority']) is not str or not profile['authority'].strip():
        raise ValueError('Explicit configuration authority required')
    if policy_mode not in ('retained-test', 'generic'):
        raise ValueError('Explicit supported scope policy mode required')
    if policy_mode == 'generic' and not production_profile:
        # Reuse only the qualified definition template. An enabled or unknown
        # input hook must be refused, never overwritten by the operator choice.
        profile_reference(profile, initialization_id, source_digest)
    authority_input = profile if policy_mode == 'retained-test' else dict(
        profile=profile, scope_policy=policy_mode, initialized_site=site_code)
    authority = hashlib.sha256(canonical(authority_input).encode()).hexdigest()
    config = definitions.configuration(profile['configuration'])
    hook, policy = ({}, {}) if production_profile else (deepcopy(profile['hook']), deepcopy(profile['disposition']))
    if policy_mode == 'generic':
        from mta.runtime import production_scope_policy as generic
        generic.text(site_code, 100, 'initialized site')
        generic.report_configuration(config)
        policy = dict(schema=generic.SCHEMA, purpose=generic.PURPOSE, site_code=site_code,
            hooks={name: generic.MODE for name in generic.HOOKS},
            input_download='enabled-five-file-four-table-archive',
            authority='Explicit VECTORFLOW_SCOPE_POLICY=generic; ' + profile['authority'])
        hook = dict(schema=generic.HOOK_SCHEMA, placement='PostBPR', mode=generic.MODE,
            site_code=site_code, authority=policy['authority'], source_sha256=authority)
    hook.update(authority=policy['authority'] if policy_mode == 'generic' else profile['authority'],
                source_sha256=authority)
    if policy_mode == 'retained-test':
        policy['authority'] = profile['authority']
    anchor = dict(schema='fresh-runtime-report-catalogue-anchor-v1', kind='INITIALIZATION',
        identity=initialization_id, output_digest=None, catalogue={},
        configuration_digest=digest(config), definition_digest=definitions.definition_digest(config),
        last_generated=definitions.last_generated(config),
        evidence=dict(authority=authority, source=source_digest))
    reference = dict(schema=request.REFERENCE,
        purpose='production-generic-placement' if policy_mode == 'generic' else 'owned-placement-publication-test',
        configuration_json=canonical(config), configuration_digest=digest(config),
        hook_json=canonical(hook), disposition_json=canonical(policy),
        catalogue_anchor_json=canonical(anchor), authority_sha256=authority)
    # Enforce exact definitions, seeds, disabled independent RRR and the selected policy version.
    request.validate_reference(reference)
    return reference


def check_request(stored, *, scope, binding_digest, batch_digest, profile_digest, resume, reconcile=False):
    """Pure state/identity gate, before any producer or selection invocation."""
    if stored is None:
        if scope in TAILS or resume or reconcile:
            raise ValueError('Continuation/resume requires its own recorded accepted prefix')
        return 'START'
    if any(stored[k] != v for k, v in dict(binding_digest=binding_digest,
            batch_digest=batch_digest, profile_digest=profile_digest).items()):
        raise ValueError('Frozen scope input, opening or profile differs')
    origin = TAILS.get(scope, scope)
    if stored['initial_scope'] != origin:
        raise ValueError('Choose Full OR one split path in this initialized date; never mix paths')
    if reconcile:
        if (resume or stored['scope'] != scope or stored['status'] not in
                ('EXECUTING', 'FAILED', 'RECOVERABLE', 'CALCULATED')):
            raise ValueError('Reconcile requires the exact interrupted operation, without --resume')
        return 'RECONCILE'
    if stored['status'] in ('EXECUTING', 'FAILED'):
        raise ValueError('Interrupted/failed native work needs reconciliation; no automatic replay')
    if stored['status'] == 'RECOVERABLE':
        if scope not in TAILS or stored['scope'] != scope or not resume:
            raise ValueError('Reconciled continuation requires exact scope and explicit --resume')
        return 'RECOVER'
    if stored['scope'] == scope:
        if stored['status'] == 'PUBLISHED':
            return 'EXISTING'
        if stored['status'] == 'CALCULATED' and resume:
            return 'PREPARE'
        if stored['status'] == 'PREPARED' and resume:
            return 'SELECT'
        raise ValueError('Pending scope preparation requires explicit -Resume after diagnosis')
    if scope in TAILS and stored['scope'] == origin and stored['status'] == 'PUBLISHED':
        if resume:
            raise ValueError('Start the new continuation without -Resume')
        return 'CONTINUE'
    # Do not reselect an earlier phase after its tail has completed.
    if stored['scope'] in TAILS and scope == stored['initial_scope'] and stored['status'] == 'PUBLISHED':
        return 'EXISTING'
    raise ValueError('Requested scope does not match the current accepted operation')


def require_selection(actual_run, selected, expected_run, expected_digest):
    # Prefix and terminal publication can share a run ID. Their selection
    # digests differ; a run-only readiness check would admit the wrong view.
    if str(actual_run) != expected_run or selected['selection_digest'] != expected_digest:
        raise ValueError('Actual serving run or phase/terminal selection differs')


def require_profile_site(profile, initialized):
    actual = initialized.get('delivery', {}).get('site_code')
    hook = profile.get('hook', {}).get('site_code')
    disposition = profile.get('disposition', {}).get('site_code')
    if not actual or actual != hook or actual != disposition:
        raise ValueError('Scope profile site %r/%r does not match initialized site %r. '
            'No scope operation is authorized; use the supported Full csv-day path. '
            'A site/hook contract extension is required, not a renamed opening.' % (hook, disposition, actual))


def initialized_profile(owner):
    from mta.runtime.input_storage import read_input
    from mta.runtime.opening_storage import load_image
    return read_input(owner, components=('profile',), image_reader=load_image)['profile']


def selected_profile(args):
    path = Path(args.profile)
    if path.exists():
        return read_json(path)
    if getattr(args, 'policy', 'retained-test') == 'generic':
        return read_json(Path(__file__).resolve().parents[1] / 'config/production_scope_profile.json')
    raise ValueError('Explicit retained scope profile required')


def selected_reference(args, owner, profile):
    initialized = initialized_profile(owner)
    mode = getattr(args, 'policy', 'retained-test')
    if mode == 'generic':
        from mta.runtime import production_scope_policy as generic
        from mta.runtime.runtime_report_request import configuration
        site = initialized.get('delivery', {}).get('site_code')
        reference = profile_reference(profile, str(owner.pk), owner.source.digest,
            policy_mode=mode, site_code=site)
        generic.configuration(initialized, configuration(reference)[3])
        return reference
    if mode != 'retained-test':
        raise ValueError('Unknown scope policy mode')
    require_profile_site(profile, initialized)
    return profile_reference(profile, str(owner.pk), owner.source.digest)


def captured_registration(args, reference):
    """Existing work keeps its original native registration, not a live reseal."""
    if not getattr(args, 'date', None):
        return None
    path = ROOT / args.date / 'operation.json'
    receipt = read_json(path) if path.exists() else None
    if not receipt or not receipt.get('run_id'):
        return None
    from mta.runtime.models import CalculationRun
    from mta.runtime.runtime_report_registered_request import read_captured
    from mta.runtime.input_reader import read_input
    from mta.runtime.scope_runtime_reports import require_test_database
    run = CalculationRun.objects.get(pk=receipt['run_id'])
    outer = read_captured(run)
    inner = read_input(run, components=('scope_request',))['scope_request']
    if outer is None or inner['runtime_reports'] != reference:
        raise ValueError('Recorded operation differs from its captured typed registration')
    require_test_database(runtime_reports=reference, run=run)
    return dict(registration_digest=outer['registration']['registration_digest'], reference=reference)


def context(args):
    from mta.runtime import daily_feed as csv
    from mta.runtime.scope_runtime_reports import require_test_database
    from mta.runtime.production_scope import authorize
    from mta.serialization import digest
    authorize()
    binding, owner = csv.binding_owner(args.binding)
    profile = selected_profile(args)
    reference = selected_reference(args, owner, profile)
    batch, payloads, manifest = csv._batch(Path(args.input_root) / args.date, binding, args.date, Path(args.input_root))
    root = ROOT / args.date
    receipt = operation_record(root)
    decision = check_request(receipt, scope=args.scope, binding_digest=binding['_binding_digest'],
        batch_digest=manifest['digest'], profile_digest=digest(reference), resume=args.resume,
        reconcile=args.operation == 'reconcile')
    if captured_registration(args, reference) is None:
        if getattr(args, 'policy', 'retained-test') == 'generic' and args.operation == 'inspect':
            from mta.runtime import report_definition_registration as definitions
            from mta.runtime.models import InitializationCertification
            cert = InitializationCertification.objects.get(initialization=owner, status='CERTIFIED')
            definitions.register(reference, initialization_id=str(owner.pk), source_digest=owner.source.digest,
                certificate_digest=cert.receipt_digest, inspect_only=True)
        else:
            require_test_database(runtime_reports=reference)
    if decision == 'START':
        from mta.runtime.models import CalculationRun
        if CalculationRun.objects.filter(business_date=args.date, mdm_input_capture__source=owner.source).exists():
            raise ValueError('This initialized date already has a run; Full/scoped replacement is forbidden')
        csv.predecessor(owner, args.date)
        from mta.application.production_csv import parse_csv
        from mta.application.production_csv_contract import feeds
        for name, spec in feeds(binding['intake_schema']).items():
            if name in payloads:
                rows, positions = parse_csv(payloads[name], spec['columns'], name)
                del rows, positions
    if decision == 'RECOVER':
        with csv.job_lock(owner) as check:
            _verify_recovery(args, csv, binding, owner, reference, manifest, root, receipt)
            check()
    elif (receipt and receipt['status'] == 'CALCULATED' and decision != 'RECONCILE'
            and receipt.get('reconciliation', {}).get('verification', {}).get('outcome') == 'CALCULATED'):
        with csv.job_lock(owner) as check:
            _verify_recovery(args, csv, binding, owner, reference, manifest, root, receipt,
                             outcome='CALCULATED')
            check()
    if args.operation == 'inspect':
        inspect_native(args, csv, binding, owner, reference, batch, manifest, payloads, receipt, decision)
    return csv, binding, owner, reference, batch, manifest, root, receipt, decision


def pick_root():
    """The same installation-owned output root used by ordinary CSV staging."""
    root = ROOT.parent / 'pick'
    root.mkdir(parents=True, exist_ok=True)
    return root


def inspect_native(args, csv, binding, owner, reference, batch, manifest, payloads, receipt, decision):
    """Admit native input/current ownership before the launcher stops serving.

    The inner placement request validates the effects before immutable report
    registration. Its separate read-only preflight owns certificate/registration
    admission; execute rechecks the final registered attachment under its locks.
    No operation receipt or business capture is created by this inspection.
    """
    from mta.runtime import production_report_placement as engine, scoped_actions
    if decision in ('CONTINUE', 'RECOVER'):
        from mta.runtime.models import CalculationRun
        run = CalculationRun.objects.get(pk=receipt['run_id'])
        phase = run.phase_acceptances.get(phase='BPR' if args.scope == 'PostBPR' else 'DBM', state_sealed=True)
        recovery = receipt['reconciliation']['verification'] if decision == 'RECOVER' else None
        options = {'recovery_of': recovery['recovery_of']} if recovery else {}
        engine.continue_run(str(run.pk), scope=args.scope,
            expected_phase_digest=phase.digest if recovery is None else recovery['source_phase_digest'],
            expected_action_revision=scoped_actions.revision(run) if recovery is None else recovery['action_revision'],
            command_key='csv-' + args.scope + '-' + manifest['digest'],
            worker_reference='vectorflow-csv-scope', inspect_only=True, **options)
    elif decision == 'START':
        import tempfile
        from mta.runtime import production_daily, runtime_report_request
        from mta.runtime.daily_preparation import prepare
        from mta.runtime.production_preflight import require
        parent = csv.predecessor(owner, args.date)
        output = pick_root()
        work = Path(os.environ.get('VF_WORK_ROOT', str(ROOT.parent / 'work')))
        work.mkdir(parents=True, exist_ok=True)
        # Stream through the supported CSV transport, including RecordRows.
        # Only this unregistered temporary transport is released afterwards.
        with tempfile.TemporaryDirectory(prefix='scope-preflight-', dir=work) as temporary:
            raw, _positions = csv.assemble(batch, binding, payloads, first_day=parent is None,
                output_file=Path(temporary) / 'native-day.json', _transfer=True)
            prepared = prepare(raw, raw.sha256)
            parameters = csv._parameters(binding, owner, parent,
                'csv-scope-' + manifest['digest'], output)
            request = runtime_report_request.request(args.scope,
                'csv-' + args.scope + '-' + manifest['digest'], runtime_reports=reference)
            report, *_ = production_daily.inspect_execution(prepared, raw.sha256,
                scope_request=request, **parameters)
            require(report, 'day')


def register(args, *, inspect_only=False):
    """Provisioner credential only; native registration enforces its owner."""
    from mta.runtime import daily_feed as csv, report_definition_registration as definitions
    from mta.runtime.scope_runtime_reports import require_test_database
    from mta.runtime.models import InitializationCertification
    binding, owner = csv.binding_owner(args.binding)
    profile = selected_profile(args)
    reference = selected_reference(args, owner, profile)
    captured = captured_registration(args, reference)
    if captured is not None:
        target = ROOT / 'registration.json'
        if not target.exists() or read_json(target) != captured:
            raise ValueError('Original captured scope registration receipt is missing or differs')
        return dict(status='SCOPE_REGISTRATION_PREFLIGHT_READY' if inspect_only else 'SCOPE_PROFILE_REGISTERED')
    if getattr(args, 'policy', 'retained-test') != 'generic':
        require_test_database()
    cert = InitializationCertification.objects.get(initialization=owner, status='CERTIFIED')
    if getattr(args, 'policy', 'retained-test') == 'generic':
        from mta.runtime.production_scope_policy import archive_label
        archive_label(cert.database_name)
    encoded = definitions.encode(reference, initialization_id=str(owner.pk),
        source_digest=owner.source.digest, certificate_id=str(cert.pk), certificate_digest=cert.receipt_digest)
    value = dict(registration_digest=encoded['registration_digest'], reference=reference)
    target = ROOT / 'registration.json'
    if target.exists() and read_json(target) != value:
        raise ValueError('Existing scope registration differs; no replacement')
    if inspect_only:
        definitions.register(reference, initialization_id=str(owner.pk),
            source_digest=owner.source.digest, certificate_digest=cert.receipt_digest,
            inspect_only=True)
        return dict(status='SCOPE_REGISTRATION_PREFLIGHT_READY')
    registered = definitions.register(reference, initialization_id=str(owner.pk),
        source_digest=owner.source.digest, certificate_digest=cert.receipt_digest)
    if str(registered.pk) != value['registration_digest']:
        raise ValueError('Native registered scope identity differs')
    ROOT.mkdir(parents=True, exist_ok=True)
    csv.atomic_json(target, value)
    return dict(status='SCOPE_PROFILE_REGISTERED')


def _save(csv, root, receipt):
    csv.atomic_json(root / 'operation.json', receipt)
    return receipt


RECONCILIATION = 'vectorflow-csv-scope-reconciliation-v1'


def _frozen_operation(args, csv, binding, manifest, root, receipt):
    from mta.serialization import digest
    check_request(receipt, scope=args.scope, binding_digest=binding['_binding_digest'],
        batch_digest=manifest['digest'], profile_digest=receipt['profile_digest'],
        resume=False, reconcile=True)
    if (receipt.get('schema') != 'vectorflow-csv-scope-operation-v1'
            or receipt.get('date') != args.date or args.scope == 'Full'):
        raise ValueError('Reconciliation supports only the exact scoped date; Full interruption is unsupported')
    from mta.application.production_csv_files import contained, regular
    original = contained(root / 'original', root)
    frozen = read_json(regular(original / 'snapshot.json', root))
    names = set(manifest['files'])
    if (frozen != manifest or {path.name for path in original.iterdir()} != names | {'snapshot.json'}
            or any(csv.file_identity(regular(original / name, root)) != manifest['files'][name]
                   for name in names)):
        raise ValueError('Frozen scope originals or snapshot receipt differ')
    if (csv.file_identity(regular(root / 'native-day.json', root))['sha256']
            != receipt.get('native_sha256')):
        raise ValueError('Frozen scope originals or native input differ')
    return digest(receipt)


def _attempt_evidence(attempt):
    """Finite immutable worker evidence, excluding its authentication token."""
    from mta.serialization import storage
    names = ('id', 'run_id', 'scope', 'command_key', 'attempt_no', 'recovery_of_id',
        'expected_phase', 'expected_receipt_digest', 'input_digest', 'input_manifest_digest',
        'compatibility_digest', 'action_revision', 'worker_reference', 'status', 'failure',
        'revision_before', 'revision_after', 'revision_closed', 'created_at', 'finished_at')
    return storage({name: str(value) if name in ('id', 'run_id', 'recovery_of_id') and value is not None
                    else value for name in names for value in (getattr(attempt, name),)})


def _reconciliation_owner(args, binding, owner, reference, receipt):
    """Pure authentication after source/run locks; never call an execute entry."""
    from mta.runtime import production_scope as original, runtime_report_request as requests
    from mta.runtime.input_reader import read_input
    from mta.runtime.runtime_report_registered_request import read_captured
    from mta.runtime.models import CalculationRun
    from mta.runtime import scope_execution as workers
    parameters = receipt['parameters']
    if (str(parameters.get('initialization_id')) != str(owner.pk)
            or parameters.get('source_digest') != owner.source.digest
            or parameters.get('configuration_digest') != binding['configuration_digest']
            or parameters.get('execution_revision') != 'csv-scope-' + receipt['batch_digest']):
        raise ValueError('Recorded scope parameters differ from the bound initialization/source')
    candidates = list(CalculationRun.objects.filter(kind='DAILY_CHAIN', business_date=args.date,
        execution_revision=parameters['execution_revision'], mdm_input_capture__source=owner.source)[:2])
    if len(candidates) != 1 or receipt.get('run_id') not in (None, str(candidates[0].pk)):
        raise ValueError('Reconciliation requires one exact own source/date/run')
    workers._source_lock(candidates[0].pk)
    run = CalculationRun.objects.select_for_update().get(pk=candidates[0].pk)
    raw = read_input(run, components=('scope_request', 'initialization_binding', 'daily_input_sha256',
        'pick_output_root', 'lineage'))
    captured = requests.validate_request(raw['scope_request'], run=run)
    registered = read_json(ROOT / 'registration.json')
    outer = read_captured(run)
    from mta.runtime.temporal import resolved_pick_root
    if (captured['scope'] != receipt['initial_scope']
            or captured['command_key'] != 'csv-' + receipt['initial_scope'] + '-' + receipt['batch_digest']
            or captured['runtime_reports'] != reference or registered.get('reference') != reference
            or outer is None or outer['registration']['registration_digest'] != registered.get('registration_digest')
            or outer['registration']['initialization_id'] != str(owner.pk)
            or outer['registration']['source_digest'] != owner.source.digest
            or raw['initialization_binding']['id'] != str(owner.pk)
            or raw['initialization_binding']['source_digest'] != owner.source.digest
            or raw['initialization_binding']['configuration_digest'] != binding['configuration_digest']
            or raw['daily_input_sha256'] != receipt['native_sha256']
            or raw['pick_output_root'] != resolved_pick_root(parameters['pick_output_root'])
            or (str(run.predecessor_id) if run.predecessor_id else None) != parameters.get('predecessor_id')
            or raw['lineage'].get('output_digest') != parameters.get('predecessor_output_digest')
            or run.business_date.isoformat() != args.date
            or run.mdm_input_capture.source_id != owner.source.pk):
        raise ValueError('Captured scope, registration, frozen input or source/date binding differs')
    original.captured_run(run, captured)
    return run, captured


def _reconciliation_state(args, run, captured, receipt=None):
    """Read existing accepted owners only; no claim, fence, repair or producer."""
    from mta.runtime import production_scope as original, scope_execution as workers
    from mta.runtime import production_report_placement as engine, scoped_actions, scope_revisions
    latest = run.scope_attempts.select_for_update().order_by('-created_at', '-id').first()
    if latest is None or run.scope_attempts.filter(status='ACTIVE').exists():
        raise ValueError('Reconciliation refuses an absent or active worker; explicit fencing is separate')
    head = workers.head(run.pk)
    action = scoped_actions.revision(run)
    command = 'csv-' + args.scope + '-' + args._batch_digest
    source_name = 'BPR' if captured['scope'] == 'UptoBPR' else 'DBM'
    source = run.phase_acceptances.select_related('attempt').get(phase=source_name, state_sealed=True)
    source = original._phase(run, source_name, source.digest)
    if (source.attempt.status != 'RELEASED' or source.attempt.scope != captured['scope']
            or source.attempt.command_key != captured['command_key']
            or source.attempt.compatibility_digest != captured['compatibility_digest']
            or latest.compatibility_digest != captured['compatibility_digest']
            or latest.input_digest != run.input_digest or latest.input_manifest_digest != run.input_manifest_digest
            or latest.action_revision != action or latest.worker_reference != 'vectorflow-csv-scope'):
        raise ValueError('Reconciliation worker/source/command/compatibility/action ownership differs')
    proof = dict(run_id=str(run.pk), scope=args.scope, command_key=command,
        compatibility_digest=captured['compatibility_digest'], source_phase_id=str(source.pk),
        source_phase_digest=source.digest, accepted_head=list(head), action_revision=action,
        latest_attempt=_attempt_evidence(latest))
    if (args.scope in TAILS and run.status == 'RUNNING' and latest.pk == source.attempt.pk
            and latest.status == 'RELEASED' and head == (source_name, source.digest)):
        prefix = (receipt or {}).get('results', {}).get(captured['scope'], {})
        if (run.scope_attempts.filter(scope__in=tuple(TAILS)).exists()
                or (receipt or {}).get('scope') != args.scope
                or (receipt or {}).get('status') not in ('EXECUTING', 'FAILED', 'RECOVERABLE')
                or prefix.get('run_id') != str(run.pk)
                or prefix.get('phase_acceptance_id') != str(source.pk)
                or prefix.get('phase_acceptance_digest') != source.digest
                or prefix.get('snapshot_digest') != source.snapshot.state_digest):
            raise ValueError('Unclaimed continuation requires its exact unchanged released prefix')
        # The public prefix result has no action_revision field. The released
        # native owner's action_revision == current action was checked above.
        scope_revisions.require_current(run)
        return dict(proof, outcome='RECOVERABLE', recovery_of=None, continuation_never_claimed=True), None
    if latest.scope != args.scope or latest.command_key != command:
        raise ValueError('Reconciliation latest continuation scope/command differs')
    if args.scope in TAILS and run.status == 'RUNNING':
        if (latest.status != 'FAILED' or hasattr(latest, 'recovery')
                or head[0] not in (('BPR', 'DBM') if args.scope == 'PostBPR' else ('DBM',))):
            raise ValueError('Recovery requires its exact latest failed continuation and accepted head')
        original._phase(run, head[0], head[1])
        scope_revisions.require_current(run)
        return dict(proof, outcome='RECOVERABLE', recovery_of=str(latest.pk)), None
    if args.scope in TAILS and run.status == 'SUCCEEDED':
        result = engine._continued(run, captured, scope=args.scope, command_key=command, expected_revision=action)
        if result['attempt_id'] != str(latest.pk):
            raise ValueError('Completed continuation is not the latest released owner')
    elif args.scope == captured['scope'] and run.status == 'RUNNING':
        if latest.status != 'RELEASED' or latest.pk != source.attempt.pk or head != (source_name, source.digest):
            raise ValueError('Journal repair requires the latest exact released prefix')
        from mta.runtime.scoped_pick_files import read as read_pick
        from mta.runtime.runtime_report_placement_publication import read as read_publication
        bpr = run.phase_acceptances.get(phase='BPR', state_sealed=True)
        files = read_pick(bpr.pk, expected_digest=bpr.digest)
        publication = read_publication(run.pk,
            placement='PostBPR' if source_name == 'BPR' else 'PostDBM', verify_bytes=True)
        result = dict(scope=args.scope, run_id=str(run.pk), status=run.status,
            phase_acceptance_id=str(source.pk), phase_acceptance_digest=source.digest,
            snapshot_digest=source.snapshot.state_digest, action_revision=action,
            pick_files_digest=files.digest, calculation_accepted=True, serving_selected=False,
            application_acceptance=False, runtime_reports=dict(ready=True,
                publication_id=str(publication.pk), publication_digest=publication.digest))
    else:
        raise ValueError('Interrupted operation has no supported accepted result; no general recovery')
    from mta.serialization import digest
    return dict(proof, outcome='CALCULATED', recovery_of=None, accepted_result_digest=digest(result)), result


def _append_reconciliation(root, original, verification):
    """Install complete immutable evidence before replacing the mutable journal."""
    from tempfile import NamedTemporaryFile
    from mta.serialization import digest
    evidence = dict(schema=RECONCILIATION, original_operation=original, verification=verification)
    checksum = digest(evidence)
    directory = root / 'reconciliations'
    directory.mkdir(exist_ok=True)
    target = directory / (checksum + '.json')
    candidate = None
    try:
        with NamedTemporaryFile(dir=directory, prefix='.reconcile-', delete=False) as stream:
            candidate = Path(stream.name)
            stream.write((canonical(evidence) + '\n').encode())
            stream.flush(); os.fsync(stream.fileno())
        try: os.link(candidate, target)
        except FileExistsError: pass
        if target.is_symlink() or read_json(target) != evidence:
            raise ValueError('Immutable reconciliation evidence differs')
        if os.name == 'posix':
            descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(descriptor)
            finally: os.close(descriptor)
    finally:
        if candidate is not None: candidate.unlink(missing_ok=True)
    return dict(schema=RECONCILIATION, evidence_digest=checksum, verification=verification)


def _reconciliation_evidence(root, receipt):
    from mta.serialization import digest
    value = receipt.get('reconciliation')
    if (type(value) is not dict or set(value) != {'schema', 'evidence_digest', 'verification'}
            or value['schema'] != RECONCILIATION or type(value['evidence_digest']) is not str
            or len(value['evidence_digest']) != 64
            or any(c not in '0123456789abcdef' for c in value['evidence_digest'])):
        raise ValueError('Exact immutable reconciliation evidence required')
    evidence = read_json(root / 'reconciliations' / (value['evidence_digest'] + '.json'))
    if (digest(evidence) != value['evidence_digest'] or evidence.get('schema') != RECONCILIATION
            or evidence.get('verification') != value['verification']):
        raise ValueError('Reconciliation evidence changed')
    original = evidence['original_operation']
    expected = deepcopy(original)
    expected.update(run_id=value['verification']['run_id'], status=value['verification']['outcome'],
                    reconciliation=value)
    if receipt['status'] == 'CALCULATED':
        expected['results'][receipt['scope']] = receipt['results'][receipt['scope']]
        if digest(receipt['results'][receipt['scope']]) != value['verification'].get('accepted_result_digest'):
            raise ValueError('Reconciled accepted result changed')
    if expected != receipt:
        raise ValueError('Reconciled journal differs from its immutable original')
    return value['verification']


def _verify_recovery(args, csv, binding, owner, reference, manifest, root, receipt, *, outcome='RECOVERABLE'):
    from django.db import transaction
    _frozen_operation(args, csv, binding, manifest, root, receipt)
    saved = _reconciliation_evidence(root, receipt)
    with transaction.atomic():
        if read_json(root / 'operation.json') != receipt:
            raise ValueError('Scope journal changed before reconciliation verification')
        run, captured = _reconciliation_owner(args, binding, owner, reference, receipt)
        args._batch_digest = manifest['digest']
        actual, _result = _reconciliation_state(args, run, captured, receipt)
        if actual != saved or actual['outcome'] != outcome:
            raise ValueError('Reconciled recovery owner/head/action changed; reconcile again explicitly')
    return saved


def _reconcile(args, csv, binding, owner, reference, manifest, root, receipt, check):
    from django.db import transaction
    _frozen_operation(args, csv, binding, manifest, root, receipt)
    with transaction.atomic():
        run, captured = _reconciliation_owner(args, binding, owner, reference, receipt)
        args._batch_digest = manifest['digest']
        verification, result = _reconciliation_state(args, run, captured, receipt)
        if receipt['status'] in ('RECOVERABLE', 'CALCULATED'):
            if _reconciliation_evidence(root, receipt) != verification:
                raise ValueError('Existing reconciliation owner changed; preserve it and diagnose')
            if result is not None and receipt['results'].get(args.scope) != result:
                raise ValueError('Reconciled accepted result differs')
            return receipt
        reconciled = deepcopy(receipt)
        reconciled.update(run_id=str(run.pk), status=verification['outcome'],
            reconciliation=_append_reconciliation(root, receipt, verification))
        if result is not None: reconciled['results'][args.scope] = result
        check()
        return _save(csv, root, reconciled)


def _calculate(args, csv, binding, owner, reference, batch, manifest, root, receipt, decision):
    from mta.serialization import digest
    from mta.runtime import production_report_placement as engine, scoped_actions
    from mta.runtime.models import CalculationRun
    if decision == 'START':
        # Refuse other date owners before freezing or starting another capture.
        if CalculationRun.objects.filter(business_date=args.date, mdm_input_capture__source=owner.source).exists():
            raise ValueError('This source/date already has a run; no Full/scoped replacement')
        root.mkdir(parents=True, exist_ok=False)
        _, frozen = csv.snapshot(Path(args.input_root) / args.date, root / 'original', Path(args.input_root))
        if frozen != manifest:
            raise ValueError('Raw input changed during snapshot')
        parent = csv.predecessor(owner, args.date)
        payloads = {name: root / 'original' / name for name, state in batch['feeds'].items() if state == 'PRESENT'}
        raw, positions = csv.assemble(batch, binding, payloads, first_day=parent is None,
            output_file=root / 'native-day.json', _transfer=True)
        csv.atomic_json(root / 'record-lines.json', positions)
        parameters = csv._parameters(binding, owner, parent, 'csv-scope-' + manifest['digest'],
                                     pick_root())
        for field in ('initialization_id', 'predecessor_id'):
            if parameters[field] is not None:
                parameters[field] = str(parameters[field])
        receipt = dict(schema='vectorflow-csv-scope-operation-v1', date=args.date,
            initial_scope=args.scope, scope=args.scope, status='VALIDATED',
            binding_digest=binding['_binding_digest'], batch_digest=manifest['digest'],
            profile_digest=digest(reference), native_sha256=raw.sha256,
            parameters=parameters, results={})
    registered = read_json(ROOT / 'registration.json')
    if registered['reference'] != reference:
        raise ValueError('Registered scope profile differs')
    command = 'csv-' + args.scope + '-' + manifest['digest']
    recovery = None
    if decision == 'RECOVER':
        recovery = _verify_recovery(args, csv, binding, owner, reference, manifest, root, receipt)
    receipt.update(scope=args.scope, status='EXECUTING')
    _save(csv, root, receipt)  # A crash here must not silently recalculate.
    try:
        if decision in ('CONTINUE', 'RECOVER'):
            run = CalculationRun.objects.get(pk=receipt['run_id'])
            phase = run.phase_acceptances.get(phase='BPR' if args.scope == 'PostBPR' else 'DBM', state_sealed=True)
            options = {} if recovery is None else {'recovery_of': recovery['recovery_of']}
            result = engine.continue_run(str(run.pk), scope=args.scope,
                expected_phase_digest=phase.digest if recovery is None else recovery['source_phase_digest'],
                expected_action_revision=scoped_actions.revision(run) if recovery is None else recovery['action_revision'],
                command_key=command, worker_reference='vectorflow-csv-scope', **options)
        else:
            from mta.application.streamed_input import JsonInputFile
            from mta.runtime.daily_preparation import prepare
            raw = JsonInputFile(root / 'native-day.json')
            if csv.file_identity(raw.path)['sha256'] != receipt['native_sha256']:
                raise ValueError('Frozen native input differs')
            prepared = prepare(raw, receipt['native_sha256'])
            result = engine.execute(prepared, receipt['native_sha256'], scope=args.scope,
                command_key=command, registration_digest=registered['registration_digest'],
                worker_reference=None if args.scope == 'Full' else 'vectorflow-csv-scope',
                **receipt['parameters'])
        receipt['results'][args.scope] = result
        receipt.update(run_id=result['run_id'], status='CALCULATED')
        return _save(csv, root, receipt)
    except Exception as error:
        receipt.update(status='FAILED', error=str(error))
        _save(csv, root, receipt)
        raise


def _prepare(csv, root, receipt, *, binding):
    from django.conf import settings
    from django.db import connection
    from mta.runtime.models import CalculationRun
    run = CalculationRun.objects.get(pk=receipt['run_id'])
    clear = {key: '' for key in ('VF_MTA_SELECTION_FILE', 'VF_MTA_PUBLISHED_RUN',
        'VF_MTA_PUBLISHED_DIGEST', 'VF_BTR_REPORTING_GENERATION', 'VF_MTA_PHASE_SELECTION_FILE',
        'VF_MTA_SCOPE_DELIVERY_FILE', 'VF_MTA_SCOPE_DELIVERY_SHA256', 'VF_MTA_SCOPE_ARTIFACT_SHA256')}
    environment = {**clear, 'VF_MDM_SOURCE_DIGEST': run.mdm_input_capture.source.digest,
                   'VF_MTA_SCOPED_BOR_OUTPUT_POLICY': 'null'}
    if receipt['scope'] in ('UptoBPR', 'UptoDBM'):
        from mta.runtime.scoped_actions import revision
        from mta.presentation import scoped_view, scoped_dbm_view, scoped_selection, scoped_artifacts
        from mta.application.production_output_policy import contract
        phase = run.phase_acceptances.get(phase='BPR' if receipt['scope'] == 'UptoBPR' else 'DBM', state_sealed=True)
        view = (scoped_view if receipt['scope'] == 'UptoBPR' else scoped_dbm_view).prepare(
            phase.pk, expected_digest=phase.digest, action_revision=revision(run))
        sources = view.bpr.sources
        from mta.runtime.input_reader import read_input
        from mta.runtime import production_scope_policy as generic
        request = read_input(run, components=('scope_request',))['scope_request']
        production = request['dispositions']['schema'] == generic.SCHEMA
        policy = dict(purpose=generic.PURPOSE if production else 'owned-scoped-test',
            run_id=str(run.pk), phase_id=str(sources.acceptance_id),
            phase_digest=sources.acceptance_digest, snapshot_digest=sources.snapshot_digest,
            output_contract=contract())
        settings.VF_MTA_SCOPED_BOR_OUTPUT_POLICY = policy
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database()')
            database = cursor.fetchone()[0]
        from mta.runtime.production_upto_dbm import archive_label
        declaration = dict(schema=scoped_artifacts.PRODUCTION_SCHEMA if production else scoped_artifacts.SCHEMA,
            purpose=generic.PURPOSE if production else 'owned-scoped-test', run_id=str(run.pk),
            phase_id=str(sources.acceptance_id), phase_digest=sources.acceptance_digest,
            input_digest=run.input_digest, input_manifest_digest=run.input_manifest_digest,
            site_code=request['dispositions']['site_code'],
            post_bpr_hook=generic.MODE if production else 'explicit-test-no-op', input_download=True,
            importer_database=generic.archive_label(database) if production else archive_label(database),
            physical_files=list(scoped_artifacts.PHYSICAL), input_tables=list(scoped_artifacts.TABLES),
            archive_clock='business-midnight-Asia-Kolkata', authority=request['dispositions']['authority'])
        path = root / 'inputdata-declaration.json'
        csv.atomic_json(path, declaration)
        pin = csv.file_identity(path)['sha256']
        artifact = scoped_artifacts.prepare(sources.acceptance_id, expected_digest=sources.acceptance_digest,
            declaration_file=str(path), declaration_sha256=pin)
        settings.VF_MTA_SCOPE_DELIVERY_FILE = str(path)
        settings.VF_MTA_SCOPE_DELIVERY_SHA256 = pin
        settings.VF_MTA_SCOPE_ARTIFACT_SHA256 = artifact['receipt_sha256']
        selection = root / 'phase-selection.json'
        scoped_selection.write(selection, scoped_selection.candidate(view))
        environment.update(VF_MTA_PHASE_SELECTION_FILE=str(selection),
            VF_MTA_SCOPE_DELIVERY_FILE=str(path), VF_MTA_SCOPE_DELIVERY_SHA256=pin,
            VF_MTA_SCOPE_ARTIFACT_SHA256=artifact['receipt_sha256'],
            VF_MTA_SCOPED_BOR_OUTPUT_POLICY=canonical(policy))
    else:
        from mta.presentation import native_publication, daily_publication, native_selection
        native = native_publication.identity(run, verify_rows=True)
        publication, summary = daily_publication.prepare_reporting_generation(run.pk,
            expected_output_digest=run.output_digest)
        # Terminal Full/tails keep the ordinary native archive contract.
        # Use this operation's frozen daily input, including across continuation;
        # the archive owner validates both originals against the captured run.
        from mta.application.native_input_archive import prepare as prepare_archive
        prepare_archive(run, binding['_opening_path'], root / 'native-day.json')
        selection = Path('/var/lib/vectorflow/selection.json')
        native_selection.write(selection, native_selection.candidate(run, publication, summary, native))
        environment.update(VF_MTA_SELECTION_FILE=str(selection), VF_MTA_PUBLISHED_RUN=str(run.pk),
            VF_MTA_PUBLISHED_DIGEST=run.output_digest,
            VF_BTR_REPORTING_GENERATION=native_selection.read(selection)['btr_generation'])
    receipt.update(status='PREPARED', environment=environment,
                   selection_digest=read_json(selection)['selection_digest'])
    return _save(csv, root, receipt)


def operation(args):
    csv, binding, owner, reference, batch, manifest, root, receipt, decision = context(args)
    if args.operation == 'inspect':
        return dict(status='EXISTING' if decision == 'EXISTING' else 'SCOPE_PREFLIGHT_READY',
            decision=decision, scope=args.scope, business_date=args.date,
            run_id=receipt.get('run_id') if receipt else None,
            selection_digest=receipt.get('selection_digest') if receipt else None,
            **({'recovery_of': receipt['reconciliation']['verification']['recovery_of']}
               if decision == 'RECOVER' else {}))
    with csv.job_lock(owner) as check:
        current = read_json(root / 'operation.json') if (root / 'operation.json').exists() else None
        if current != receipt:
            raise ValueError('Scope operation changed while acquiring ownership; inspect again')
        if decision == 'EXISTING':
            return receipt
        if decision == 'RECONCILE':
            return _reconcile(args, csv, binding, owner, reference, manifest, root, receipt, check)
        if decision in ('START', 'CONTINUE', 'RECOVER'):
            receipt = _calculate(args, csv, binding, owner, reference, batch, manifest, root, receipt, decision)
        check()
        if receipt['status'] == 'CALCULATED':
            receipt = _prepare(csv, root, receipt, binding=binding)
        check()
        return receipt


def serving(args):
    from django.conf import settings
    if settings.VF_MTA_PHASE_SELECTION_FILE:
        from mta.presentation import scoped_admission, scoped_selection
        run, identity = scoped_admission.binding()
        selected = scoped_selection.read(settings.VF_MTA_PHASE_SELECTION_FILE)
    else:
        from mta.presentation.admission import binding
        from mta.presentation.native_selection import read
        run, identity = binding()
        selected = read(settings.VF_MTA_SELECTION_FILE)
    require_selection(run.pk, selected, args.run, args.selection_digest)
    if args.admission_only:
        return dict(admitted=True, run_id=str(run.pk), admission_digest=identity,
                    selection_digest=selected['selection_digest'])
    with urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=15) as response:
        actual = json.load(response)
    if actual.get('ready') is not True or actual.get('admission_digest') != identity:
        raise ValueError('Serving process has not admitted this selected scope')
    if settings.VF_MTA_PHASE_SELECTION_FILE:
        _, after = scoped_admission.binding()
    else:
        _, after = binding()
    if after != identity:
        raise ValueError('Serving admission changed during verification')
    return dict(ready=True, run_id=str(run.pk), admission_digest=identity,
                selection_digest=selected['selection_digest'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('register', 'preflight', 'inspect', 'execute', 'reconcile', 'serving', 'acknowledge'))
    parser.add_argument('--date')
    parser.add_argument('--scope', choices=SCOPES)
    parser.add_argument('--policy', choices=('retained-test', 'generic'), default='retained-test')
    parser.add_argument('--binding', default='/onboarding/binding.json')
    parser.add_argument('--profile', default='/onboarding/config/scope-validation.json')
    parser.add_argument('--input-root', default='/incoming')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--run')
    parser.add_argument('--selection-digest')
    parser.add_argument('--proof')
    parser.add_argument('--admission-only', action='store_true')
    args = parser.parse_args()
    if args.operation not in ('register', 'serving'):
        if not args.date or date.fromisoformat(args.date).isoformat() != args.date or not args.scope:
            parser.error('Explicit canonical business date and scope required')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.mta_settings')
    if args.operation == 'serving':
        from release.daily_serving_check import configure_image
        configure_image()
    import django
    django.setup()
    if args.operation in ('register', 'preflight'):
        # Use the existing installer session/owner role adapter, not the
        # provisioner's superuser identity or a new privilege grant.
        from release.initialize_csv import installer_login
        with installer_login():
            result = register(args, inspect_only=args.operation == 'preflight')
    elif args.operation == 'serving':
        result = serving(args)
    elif args.operation == 'acknowledge':
        from mta.runtime import daily_feed as csv
        root = ROOT / args.date
        result = read_json(root / 'operation.json')
        if (result['status'] != 'PREPARED' or result['run_id'] != args.run
                or result['scope'] != args.scope or result['selection_digest'] != args.selection_digest):
            raise ValueError('Acknowledgement requires its exact prepared scope/run')
        proof = json.loads(args.proof or 'null')
        if (type(proof) is not dict or proof.get('ready') is not True
                or proof.get('run_id') != args.run or proof.get('selection_digest') != args.selection_digest):
            raise ValueError('Actual scope serving proof required')
        with urllib.request.urlopen('http://mta:8000/readyz', timeout=15) as response:
            actual = json.load(response)
        if actual.get('ready') is not True or actual.get('admission_digest') != proof.get('admission_digest'):
            raise ValueError('MTA serving identity changed before acknowledgement')
        result['status'] = 'PUBLISHED'
        _save(csv, root, result)
    else:
        result = operation(args)
    print(json.dumps(result, sort_keys=True, default=str))


if __name__ == '__main__':
    main()
