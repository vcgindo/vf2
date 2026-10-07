"""Execute retained external daily facts using only this engine's persisted state."""
from copy import deepcopy
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time
import gc
import subprocess
import sys

from django.core.management.base import BaseCommand, CommandError
from mta.runtime.temporal import execute_day, record_command, command_state
from mta.runtime.services import read_outputs
from mta.runtime.validation_storage import export_run
from parity.output_archive import OutputArchive
from mta.serialization import digest
from mta.runtime.temporal_continuation import (composed_prefix, copy_prefix_evidence,
    successor_index, validate_accepted_prefix, validate_source_transition)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('input',type=Path)
        parser.add_argument('--sha256',required=True)
        parser.add_argument('--revision',required=True)
        parser.add_argument('--evidence',type=Path,required=True)
        parser.add_argument('--through',type=int)
        parser.add_argument('--exceptions',type=Path)
        parser.add_argument('--automatic-actions', action='store_true')
        parser.add_argument('--mdm-source', help='Explicit owned MDM source ID for each daily capture')
        parser.add_argument('--mdm-source-digest', help='Expected immutable MDM source digest')
        parser.add_argument('--mdm-retry', help='Failed day-one run whose frozen MDM capture must be reused')
        parser.add_argument('--bpr-remark-horizon', type=int,
                            help='Explicit native daily BPR remark retention setting')
        parser.add_argument('--shipment-input',type=Path,
                            help='Registered standalone approved shipment supplement')
        parser.add_argument('--shipment-sha256')
        parser.add_argument('--continue-from',type=Path,
                            help='Accepted execution folder; execute exactly its next day')
        parser.add_argument('--computation-only', action='store_true',
                            help='Independent modern capture: no parity or UI acceptance is implied')
        parser.add_argument('--bounded-one-day', action='store_true',
                            help='One day with isolated predecessor verification and released unused inputs')
        parser.add_argument('--verify-prefix-only', action='store_true', help=argparse.SUPPRESS)

    def handle(self,*args,**options):
        mdm_source = None
        shipment_path,shipment_sha=options.get('shipment_input'),options.get('shipment_sha256')
        if bool(shipment_path)!=bool(shipment_sha):
            raise CommandError('Shipment supplement and expected digest must be supplied together')
        source_id, source_digest = options.get('mdm_source'), options.get('mdm_source_digest')
        retry_id = options.get('mdm_retry')
        continuation_path = options.get('continue_from')
        if continuation_path and retry_id:
            raise CommandError('Successor continuation cannot reuse a failed root capture')
        if retry_id and not source_id:
            raise CommandError('Frozen MDM retry requires an explicit bound source')
        if bool(source_id) != bool(source_digest):
            raise CommandError('MDM source ID and expected digest must be supplied together')
        if source_id:
            from mta.runtime.models import MdmSource
            try:
                mdm_source = MdmSource.objects.get(pk=source_id, digest=source_digest)
            except (MdmSource.DoesNotExist, ValueError) as error:
                raise CommandError('Owned MDM source identity differs') from error
            if options.get('bpr_remark_horizon') is None:
                raise CommandError('MDM daily publication requires explicit BPR remark horizon')
            if retry_id:
                from mta.runtime.mdm_daily_models import MdmDailyInputCapture
                if not MdmDailyInputCapture.objects.filter(run_id=retry_id, source=mdm_source,
                        run__status='FAILED', run__predecessor__isnull=True).exists():
                    raise CommandError('Frozen retry is not a failed root of this source')
        elif options.get('bpr_remark_horizon') is not None:
            raise CommandError('BPR remark horizon override requires an explicit MDM source')
        target=options['evidence']
        source_root=Path(__file__).resolve().parents[4]
        source_files={p.relative_to(source_root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((source_root/'mta').rglob('*.py'))}
        for name in ('temporal_ledger.py','temporal_policy.py','report_flaws.py','output_archive.py'):
            path=source_root/'parity'/name
            source_files[path.relative_to(source_root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        catalog=source_root/'baseline/production-state-schema.json'
        source_files[catalog.relative_to(source_root).as_posix()]=hashlib.sha256(catalog.read_bytes()).hexdigest()
        raw=options['input'].read_bytes()
        if hashlib.sha256(raw).hexdigest()!=options['sha256']:
            raise CommandError('Registered external artifact hash differs')
        artifact=json.loads(raw);case=artifact['case']
        if shipment_path:
            registrations=json.loads((source_root/'baseline/manifest.json').read_text())['retained_resources']
            if shipment_sha not in {row['sha256'] for row in registrations}:
                raise CommandError('Shipment supplement must be registered')
        if mdm_source is not None:
            registrations = json.loads((source_root/'baseline/manifest.json').read_text())['retained_resources']
            if options['sha256'] not in {row['sha256'] for row in registrations}:
                raise CommandError('MDM smoke requires a registered external artifact')
            from mta.mdm.daily_source import require_binding
            try:
                require_binding(mdm_source, artifact_sha256=options['sha256'],
                                artifact_schema=artifact.get('schema'))
            except ValueError as error:
                raise CommandError(str(error)) from error
        profile = deepcopy(case['profile'])
        if mdm_source is not None:
            profile['daily_publication'] = True
            configured = profile.setdefault('daily_publication_config', {})
            horizon = options['bpr_remark_horizon']
            if configured.get('bpr_remark_horizon', horizon) != horizon:
                raise CommandError('Pinned profile BPR remark horizon differs')
            configured['bpr_remark_horizon'] = horizon
        if options['automatic_actions']:
            from parity.temporal_ledger import validate
            from parity.temporal_policy import policy_for_case, commands_for_day
            validate(artifact)
            policy=policy_for_case(case)
        else:
            policy='retained-fixed-actions'
        through=options['through'] if options['through'] is not None else len(case['days'])-1
        if not 0<=through<len(case['days']):raise CommandError('Day index outside retained artifact')
        exceptions=json.loads(options['exceptions'].read_text()) if options['exceptions'] else {}
        if exceptions:
            from parity.report_flaws import validate_scope
            validate_scope(exceptions,options['sha256'])
        if options.get('bounded_one_day'):
            # Release the full artifact before a verifier subprocess shares this
            # worker's memory limit. Prefix validation needs dates/policy only.
            selected_day = {**deepcopy(case['days'][through]), **deepcopy(case['static_day'])}
            case = dict(case=case['case'], opening=case['opening'] if through == 0 else None,
                opening_date=case['opening_date'],profile=profile,
                commands=deepcopy(case['commands']),static_day={},
                days=[selected_day if i == through else {'business_date':row['business_date']}
                      for i,row in enumerate(case['days'])])
            del artifact, raw, selected_day
            gc.collect()
        previous=None;receipts=[];start=0;continuation=None;source_transition=None
        if continuation_path:
            continuation_path=continuation_path.resolve()
            try:
                previous_execution=json.loads((continuation_path/'execution.json').read_text())
                previous_source=json.loads((continuation_path/'source.json').read_text())
            except (OSError,ValueError,TypeError) as error:
                raise CommandError('Continuation evidence is incomplete') from error
            try:
                successor_index(previous_execution,through,case)
            except ValueError as error:
                raise CommandError(str(error)) from error
            if (previous_execution.get('artifact_sha256')!=options['sha256']
                    or previous_execution.get('artifact_days')!=len(case['days'])
                    or previous_execution.get('action_policy')!=policy
                    or previous_execution.get('report_exceptions',{})!=exceptions
                    or previous_source.get('execution_revision')!=previous_execution.get('revision')):
                raise CommandError('Continuation input/policy/span identity differs')
            if previous_execution.get('computation_only',False) != options.get('computation_only',False):
                raise CommandError('Continuation verification mode differs')
            expected_mdm=(dict(id=str(mdm_source.pk),digest=mdm_source.digest,
                bpr_remark_horizon=options['bpr_remark_horizon']) if mdm_source is not None else None)
            if previous_execution.get('mdm_source')!=expected_mdm:
                raise CommandError('Continuation MDM source/horizon identity differs')
            prior_shipments={row.get('shipment_supplement_sha256')
                             for row in previous_execution['days']}
            if prior_shipments!={shipment_sha}:
                raise CommandError('Continuation shipment supplement identity differs')
            try:
                source_transition=validate_source_transition(previous_source,source_files)
                if options.get('bounded_one_day') and not options.get('verify_prefix_only'):
                    result = subprocess.run([sys.executable, *sys.argv, '--verify-prefix-only'],
                        check=True, capture_output=True, text=True)
                    verified = json.loads(result.stdout)
                    from mta.runtime.models import CalculationRun
                    previous = CalculationRun.objects.get(pk=verified['predecessor_id'])
                    if str(previous.pk) != previous_execution['days'][-1]['run_id']:
                        raise ValueError('Isolated predecessor verification identity differs')
                else:
                    previous=validate_accepted_prefix(continuation_path,previous_execution,case,
                        require_parity=not options.get('computation_only',False))
            except (KeyError,ValueError,OSError) as error:
                raise CommandError(str(error)) from error
            receipts=composed_prefix(previous_execution)
            start=len(receipts)

        if options.get('verify_prefix_only'):
            if not continuation_path:
                raise CommandError('Prefix verification requires a continuation')
            self.stdout.write(json.dumps(dict(predecessor_id=str(previous.pk))))
            return
        if options.get('bounded_one_day'):
            if through != start:
                raise CommandError('Bounded worker must execute exactly one new day')

        target.mkdir(parents=True,exist_ok=False)
        if continuation_path:
            try:
                copied=copy_prefix_evidence(continuation_path,target,previous_execution)
            except (ValueError,OSError) as error:
                raise CommandError(str(error)) from error
            continuation=dict(path=str(continuation_path/'execution.json'),
                sha256=hashlib.sha256((continuation_path/'execution.json').read_bytes()).hexdigest(),
                source_sha256=hashlib.sha256((continuation_path/'source.json').read_bytes()).hexdigest(),
                copied_prefix_evidence=copied)
        source_record=dict(execution_revision=options['revision'],files=source_files)
        if source_transition is not None:source_record['transition']=source_transition
        (target/'source.json').write_text(json.dumps(source_record,indent=2),encoding='utf-8')

        for index in range(start,through+1):
            started=time.monotonic()
            day={**deepcopy(case['days'][index]),**deepcopy(case['static_day'])}
            receipt=dict(day_index=index,date=day['business_date'],status='RUNNING',
                         input_sha256=options['sha256'],execution_revision=options['revision'])
            try:
                if shipment_path:
                    from mta.presentation.daily_shipment_input import load_day
                    day['shipment_input']=load_day(shipment_path,expected_sha256=shipment_sha,
                        business_date=day['business_date'],base_artifact_sha256=options['sha256'])
                    receipt['shipment_supplement_sha256']=shipment_sha
                capture_arguments = {'mdm_source': mdm_source} if mdm_source is not None else {}
                if retry_id and index == 0:
                    capture_arguments = {'mdm_retry': retry_id}
                    receipt['retry_of'] = str(retry_id)
                run=execute_day(day=day,profile=profile,execution_revision=options['revision'],
                    predecessor=previous,opening=None if previous else dict(state=case['opening'],
                        opening_date=case['opening_date'],identity=case['case']+'-'+options['sha256']+'-'+policy),
                    report_exceptions=exceptions, **capture_arguments)
                manifest=export_run(run,target/f'day-{index:03d}')
                archive=OutputArchive(manifest)
                output=read_outputs(run)
                receipt.update(status='COMPUTED_NOT_YET_PARITY',run_id=str(run.pk),
                    predecessor_id=str(run.predecessor_id) if run.predecessor_id else None,
                    input_digest=run.input_digest,output_digest=run.output_digest,
                    closing_digest=digest(output['ClosingState']),
                    output_archive=str(manifest.relative_to(target)),
                    boundaries=[r['boundary'] for r in archive.iter_rows('MajorBoundaries')],
                    suggestions=len(output['DBMFinal'][0]['Suggestions']),commands=[])
                commands=(commands_for_day(case,index,output['DBMFinal'][0]['Suggestions'])
                          if options['automatic_actions'] else
                          [c for c in case['commands'] if c['after_day']==index])
                if options['automatic_actions']:
                    intended = {tuple(key) for event in case['commands']
                        if event['after_day']==index and event['operation']=='SLEEP'
                        for key in event['selected']}
                    actual = {tuple(key) for event in commands if event['operation']=='SLEEP'
                              for key in event['selected']}
                    receipt['action_coverage'] = dict(sleep_intended=sorted(intended),
                        sleep_exercised=sorted(actual), sleep_not_exercised=sorted(intended-actual))
                # Export/checksums are complete. Commands independently verify
                # persisted outputs; do not hold another entire trace meanwhile.
                del output
                for position,command in enumerate(commands):
                    event=record_command(run,operation=command['operation'],selected=command['selected'],
                        timestamp=command['timestamp'],actor='retained-synthetic-trial',
                        idempotency_key=policy+'-command-'+str(position))
                    receipt['commands'].append(dict(id=event.pk,command=command,digest=event.digest,
                                                     before=event.before_digest,after=event.after_digest))
                after,events=command_state(run,read_outputs(run)['DBMFinal'][0])
                with gzip.open(target/f'actions-{index:03d}.json.gz','wt',encoding='utf-8',compresslevel=1) as stream:
                    json.dump(dict(state=after,events=events),stream,sort_keys=True,separators=(',',':'))
                receipt['post_action_state_digest']=digest(after)
                previous=run
            except Exception as error:
                receipt.update(status='FAILED',error_type=type(error).__name__,error=str(error))
                raise
            finally:
                receipt['seconds']=round(time.monotonic()-started,3)
                receipts.append(receipt)
                (target/'execution.json').write_text(json.dumps(dict(
                    artifact_sha256=options['sha256'],revision=options['revision'],
                    requested_days=through+1,artifact_days=len(case['days']),
                    **({'mdm_source': dict(id=str(mdm_source.pk), digest=mdm_source.digest,
                        bpr_remark_horizon=options['bpr_remark_horizon'])} if mdm_source is not None else {}),
                    action_policy=policy,report_exceptions=exceptions,
                    computation_only=options.get('computation_only',False),
                    **({'continuation':continuation} if continuation else {}),
                    days=receipts),indent=2),encoding='utf-8')
                self.stdout.write(json.dumps(receipt));self.stdout.flush()
