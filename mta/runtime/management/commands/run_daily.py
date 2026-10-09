"""Execute exactly one declared day; never select a serving run or infer actions."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from django.core.management.base import BaseCommand, CommandError
from mta.runtime.daily_bindings import (apply_finalization, apply_operational_sources,
    apply_pick, verify_sha256, shipment_day)
from mta.runtime.models import CalculationRun, MdmSource
from mta.runtime.temporal import execute_day


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('input', type=Path)
        parser.add_argument('--sha256', required=True)
        parser.add_argument('--day-index', type=int, required=True)
        parser.add_argument('--revision', required=True)
        parser.add_argument('--evidence-mode', choices=('production','validation'), default='production')
        parser.add_argument('--predecessor')
        parser.add_argument('--mdm-source', required=True)
        parser.add_argument('--mdm-source-digest', required=True)
        parser.add_argument('--bpr-remark-horizon', type=int, required=True)
        parser.add_argument('--exceptions', type=Path)
        parser.add_argument('--finalization-config', type=Path)
        parser.add_argument('--finalization-config-sha256')
        parser.add_argument('--complete-pick-policy')
        parser.add_argument('--pick-output-root', type=Path)
        parser.add_argument('--pick-config', type=Path)
        parser.add_argument('--pick-config-sha256')
        parser.add_argument('--shipment-input',type=Path)
        parser.add_argument('--shipment-sha256')
        parser.add_argument('--operational-sources')
        parser.add_argument('--operational-input-sources')
        parser.add_argument('--operational-force-sources')

    def handle(self, *args, **options):
        raw=options['input'].read_bytes()
        if hashlib.sha256(raw).hexdigest()!=options['sha256']:
            raise CommandError('Frozen artifact identity differs')
        artifact=json.loads(raw);case=artifact['case'];index=options['day_index']
        if not 0<=index<len(case['days']):raise CommandError('Day index outside artifact')
        if bool(index)!=bool(options['predecessor']):
            raise CommandError('Only day zero uses an opening; every successor requires its predecessor')
        source=MdmSource.objects.get(pk=options['mdm_source'],digest=options['mdm_source_digest'])
        from mta.mdm.daily_source import require_binding
        require_binding(source,artifact_sha256=options['sha256'],artifact_schema=artifact.get('schema'))
        parent=CalculationRun.objects.get(pk=options['predecessor']) if index else None
        if parent and parent.business_date.isoformat()!=case['days'][index-1]['business_date']:
            raise CommandError('Predecessor date does not match the frozen preceding day')
        profile=deepcopy(case['profile'])
        bound_opening=deepcopy(case['opening'])
        bindings={}
        finalization_path=options.get('finalization_config')
        finalization_sha=options.get('finalization_config_sha256')
        if bool(finalization_path)!=bool(finalization_sha):
            raise CommandError('Finalization supplement and digest must be supplied together')
        if finalization_path:
            try:
                finalization_content=finalization_path.read_bytes()
                profile,bound_opening=apply_finalization(profile,bound_opening,
                    finalization_content,artifact_sha256=options['sha256'],
                    config_sha256=finalization_sha,
                    business_date=case['days'][0]['business_date'])
            except (OSError,ValueError,TypeError) as error:
                raise CommandError(str(error)) from error
            bindings['finalization_config']=finalization_content
        pick_values=(options.get('complete_pick_policy'),options.get('pick_output_root'),
                     options.get('pick_config'),options.get('pick_config_sha256'))
        if any(value is not None for value in pick_values) and not all(
                value is not None for value in pick_values):
            raise CommandError(
                'Complete Pick policy, output root, configuration and digest must be supplied together')
        if all(value is not None for value in pick_values):
            pick_policy,pick_output_root,pick_config_path,pick_config_sha=pick_values
            try:
                pick_output_root=pick_output_root.resolve(strict=True)
                pick_config_bytes=pick_config_path.read_bytes()
                verify_sha256(pick_config_bytes,pick_config_sha,
                              'Complete Pick configuration')
                profile=apply_pick(profile,pick_config_bytes,pick_policy)
            except (OSError,ValueError,TypeError) as error:
                raise CommandError(str(error)) from error
            bindings.update(pick_output_root=pick_output_root,
                            pick_config_sha256=pick_config_sha)
        source_policies=(options.get('operational_sources'),
                         options.get('operational_input_sources'),
                         options.get('operational_force_sources'))
        if any(value is not None for value in source_policies) and not all(
                value is not None for value in source_policies):
            raise CommandError(
                'All operational source capture policies must be supplied together')
        if all(value is not None for value in source_policies):
            try:
                profile=apply_operational_sources(profile,*source_policies)
            except ValueError as error:
                raise CommandError(str(error)) from error
        profile['daily_publication']=True
        config=profile.setdefault('daily_publication_config',{})
        horizon=options['bpr_remark_horizon']
        if config.get('bpr_remark_horizon',horizon)!=horizon:
            raise CommandError('Pinned remark horizon differs')
        config['bpr_remark_horizon']=horizon
        day={**deepcopy(case['days'][index]),**deepcopy(case['static_day'])}
        shipment_path,shipment_sha=options.get('shipment_input'),options.get('shipment_sha256')
        if bool(shipment_path)!=bool(shipment_sha):
            raise CommandError('Shipment supplement and digest must be supplied together')
        if shipment_path:
            if 'shipment_input' in day:raise CommandError('Shipment supplement cannot replace artifact facts')
            try:
                day['shipment_input']=shipment_day(shipment_path,shipment_sha,
                    artifact_sha256=options['sha256'],business_date=day['business_date'])
                bindings['shipment_sha256']=shipment_sha
            except (OSError,ValueError) as error:raise CommandError(str(error)) from error
        exceptions=json.loads(options['exceptions'].read_text()) if options['exceptions'] else {}
        opening=None if parent else dict(state=bound_opening,opening_date=case['opening_date'],
            identity=case['case']+'-'+options['sha256']+'-daily')
        started=time.monotonic()
        run=execute_day(day=day,profile=profile,execution_revision=options['revision'],
            predecessor=parent,opening=opening,mdm_source=source,
            evidence_mode=options['evidence_mode'],report_exceptions=exceptions,
            **bindings)
        self.stdout.write(json.dumps(dict(status=run.status,run_id=str(run.pk),
            business_date=run.business_date.isoformat(),input_digest=run.input_digest,
            output_digest=run.output_digest,validation_digest=run.validation_digest,
            evidence_mode=run.evidence_mode,seconds=round(time.monotonic()-started,3),
            publication='unselected; parity and preparation are separate')))
