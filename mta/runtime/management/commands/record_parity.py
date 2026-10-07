"""Attach an existing independent comparison receipt; never compute or waive parity."""
import hashlib
import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
from mta.runtime.temporal import BOUNDARIES
from parity.replay_temporal import independent_contracts_pass

CONTRACTS = (*BOUNDARIES, *('calculation/'+name for name in (
    'pick_remaining','additional_master','stock','routes','order_bpp','advance_stock',
    'git_advance','requirements','bands','pso_ration','normal_ration','bifurcation',
    'supplier_bor','bor_oa','logistic_pick')),
    'master/dbm_master','master/norm_change_export','master/importer_master',
    'master/norm_change_export_remaining','master/bpr_master','emitted-reports')


def verify_preserved_summary(root, existing, summary, entry, replay):
    """Keep an accepted prefix link only after rechecking its exact old proof."""
    if existing.get('status') not in ('PASS', 'PASS_WITH_LEGACY_FLAWS'):
        raise CommandError('Existing prefix is not accepted')
    if {k:v for k,v in existing.items() if k not in ('receipt','sha256')} != {
            k:v for k,v in summary.items() if k not in ('receipt','sha256')}:
        raise CommandError('Existing prefix comparison summary differs')
    path = (root / existing['receipt']).resolve()
    if not path.is_relative_to(root):
        raise CommandError('Existing prefix receipt is outside evidence root')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != existing['sha256']:
        raise CommandError('Existing prefix receipt digest differs')
    prior = json.loads(raw)
    if (prior['input_sha256'] != replay['input_sha256']
            or prior['action_policy'] != replay['action_policy']
            or prior['status'] not in ('PASS', 'COMPLETE_WITH_LEGACY_FLAWS')):
        raise CommandError('Existing prefix receipt identity differs')
    index = existing['day_index']
    if index >= len(prior['days']):
        raise CommandError('Existing prefix receipt lacks day')
    old = prior['days'][index]
    for field in ('day_index','date','status','modern_run','modern_output_digest','comparisons'):
        if old[field] != entry[field]:
            raise CommandError('Existing prefix day proof differs: '+field)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--replay', type=Path, required=True)
        parser.add_argument('--modern-execution', type=Path, required=True)
        parser.add_argument('--preserve-existing', action='store_true',
                            help='Verify and retain accepted prefix receipt links unchanged')
        parser.add_argument('--daily-source-proof',type=Path,
                            help='Independent offline RRR SQL proof for the new terminal day')

    def handle(self, *args, **options):
        root = Path(os.environ['VF_EVIDENCE_ROOT']).resolve().parent
        paths = [options[name].resolve() for name in ('replay', 'modern_execution')]
        if any(not path.is_relative_to(root) for path in paths):
            raise CommandError('Comparison receipts must remain under the evidence root')
        replay_path, modern_path = paths
        replay_bytes, modern_bytes = replay_path.read_bytes(), modern_path.read_bytes()
        replay, modern = json.loads(replay_bytes), json.loads(modern_bytes)
        if (replay['modern_execution_sha256'] != hashlib.sha256(modern_bytes).hexdigest()
                or replay['input_sha256'] != modern['artifact_sha256']
                or replay['action_policy'] != modern['action_policy']):
            raise CommandError('Comparison/input/action identity differs')
        if replay['status'] not in ('PASS', 'COMPLETE_WITH_LEGACY_FLAWS', 'DIVERGENCE'):
            raise CommandError('Receipt is not a completed qualified comparison')
        expected = list(CONTRACTS)
        if modern['action_policy'] != 'retained-fixed-actions':
            from parity.temporal_policy import POLICIES
            if modern['action_policy'] not in POLICIES:
                raise CommandError('Unrecognized action policy')
            expected += ['own-action-selection', 'post-action-state']
        qualified_run = any(day['status'] == 'PASS_WITH_LEGACY_FLAWS' for day in replay['days'])
        failed_run = any(day['status'] == 'DIVERGENCE' for day in replay['days'])
        aggregate = 'DIVERGENCE' if failed_run else 'COMPLETE_WITH_LEGACY_FLAWS' if qualified_run else 'PASS'
        if (not replay['days'] or len(replay['days']) > replay['requested_days']
                or (not failed_run and len(replay['days']) != replay['requested_days'])
                or replay['status'] != aggregate):
            raise CommandError('Receipt span or aggregate qualification differs')
        with transaction.atomic():
            for index, entry in enumerate(replay['days']):
                current = modern['days'][index]
                checks = entry['comparisons']
                names = [row['contract'] for row in checks]
                failed = entry['status'] == 'DIVERGENCE'
                valid = (names == expected and independent_contracts_pass(checks))
                if failed:
                    # Preserve the comparator's first-divergence stopping rule.
                    # Unexecuted contracts remain visible, never inferred PASS.
                    valid = (0 < len(checks) <= len(expected) and names == expected[:len(checks)]
                        and checks[-1]['status'] == 'FAIL' and independent_contracts_pass(checks[:-1])
                        and index == len(replay['days'])-1)
                if (entry['day_index'] != index or current['day_index'] != index
                        or not valid):
                    raise CommandError('Incomplete comparison roster or unresolved mismatch')
                run = CalculationRun.objects.select_for_update().get(pk=current['run_id'])
                if (str(run.pk) != entry['modern_run'] or run.output_digest != entry['modern_output_digest']
                        or run.output_digest != current['output_digest'] or run.input_digest != current['input_digest']
                        or run.business_date.isoformat() != entry['date']
                        or run.execution_revision != current.get('execution_revision', modern['revision'])):
                    raise CommandError('Compared run/output identity differs')
                read_outputs(run)
                if modern['action_policy'] != 'retained-fixed-actions':
                    from mta.runtime.validation_storage import read_input
                    from parity.temporal_policy import policy_for_case
                    if policy_for_case({'profile': read_input(run)['profile']}) != modern['action_policy']:
                        raise CommandError('Compared action policy differs from captured run input')
                qualified = any(row['status'] == 'LEGACY_FLAW' for row in checks)
                expected_status = 'DIVERGENCE' if failed else 'PASS_WITH_LEGACY_FLAWS' if qualified else 'PASS'
                if entry['status'] != expected_status:
                    raise CommandError('Receipt mislabels qualified legacy-flaw evidence')
                summary = dict(receipt=str(replay_path.relative_to(root)),
                    sha256=hashlib.sha256(replay_bytes).hexdigest(), day_index=index,
                    artifact_sha256=replay['input_sha256'], status=expected_status,
                    boundaries=list(BOUNDARIES), comparisons={**dict.fromkeys(expected,'NOT_RUN'),
                        **{row['contract']:row['status'] for row in checks}},
                    legacy_flaw_is_parity=False)
                from mta.runtime.offline_rrr_models import OfflineRrrColourSource
                if not failed and OfflineRrrColourSource.objects.filter(run=run).exists():
                    from mta.presentation.offline_rrr import proof_identity, require_proof
                    if run.parity_summary.get('offline_rrr_proof'):
                        summary['offline_rrr_proof']=require_proof(run)
                    elif options.get('daily_source_proof') and index==len(replay['days'])-1:
                        summary['offline_rrr_proof']=proof_identity(run,options['daily_source_proof'])
                    else:
                        raise CommandError('Each offline day needs independent source acceptance')
                if options.get('preserve_existing') and getattr(run, 'parity_summary', None):
                    verify_preserved_summary(root, run.parity_summary, summary, entry, replay)
                    continue
                # Prefix evidence remains on disk. Updating its link after a
                # longer same-run comparison never mutates any original receipt.
                run.parity_summary = summary
                run.save(update_fields=['parity_summary'])
        self.stdout.write(f"Recorded {len(replay['days'])} run comparison summaries; no populations imported.")
