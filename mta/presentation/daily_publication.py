"""Finite, explicit daily UI preparation; never selects a calculated run.

Each layer owns its immutable typed receipt. A failed attempt keeps all existing
receipts and diagnostics and can reuse unchanged successes. Engine acceptance
and human UI acceptance remain separate from preparation readiness.
"""
import inspect
import json
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from mta.runtime.models import CalculationRun, DailyUiPublication, DailyUiPublicationAttempt
from mta.serialization import digest
from mta.presentation.context import PublicationUnavailable
from mta.presentation.request_scope import once_per_request
from mta.application.stage_observation import stage,summary

CONFIG_NAMES = ('VF_MTA_PERMISSIONS_SHA256', 'VF_MTA_HIERARCHY_SHA256',
    'VF_MTA_ACTIONS_ENABLED', 'VF_MTA_ACTION_TIME_ZONE', 'VF_BPR_PREPARED',
    'VF_GUIDED_PREPARED', 'VF_RRR_PREPARED', 'VF_HISTORY_REPORTS_PREPARED',
    'VF_RESEARCH_AVAILABILITY_PREPARED', 'VF_MTA_SYNTHETIC_ROSTER')


def configuration_identity(*, access=None):
    from pathlib import Path
    import hashlib
    root = Path(__file__).resolve().parents[1] / 'config'
    values = {name: getattr(settings, name) for name in CONFIG_NAMES}
    from mta.presentation import native_publication
    if native_publication.enabled():
        native_publication.require_mode()
        values['native_publication'] = True
    if access is not None:
        values.update({name: access[name] for name in ('VF_MTA_PERMISSIONS_SHA256', 'VF_MTA_HIERARCHY_SHA256')})
    return digest(dict(settings=values, configs={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.json'))}))


@once_per_request
def recipe_identity():
    from mta.presentation import daily_preparation
    # Coordinator implementation is artifact provenance, not a persisted data
    # format. Layer producers retain their own source/dependency identities.
    return digest(dict(contract='daily-ui-publication-v1',
        roster=daily_preparation.roster_identity(),layers=daily_preparation.required_layers()))


def supported_recipe(recipe):
    # The deployed v1 format predates an explicit coordinator contract. This
    # single historical decoder boundary preserves that format without rewriting
    # old receipts. Future code-only patches use recipe_identity unchanged.
    return recipe in (recipe_identity(),
        '229b0219c8fa70cb4c9e503345d1450e233d4b555c06fe5331bbdf8354d4c870')


def source_identity(run):
    from mta.presentation.daily_sources import receipt
    source = receipt(run)
    value = dict(input=run.input_digest, output=run.output_digest, production=run.production_digest, manifest=run.production_manifest, daily_sources=source.images_digest, daily_recipe=source.recipe_digest)
    from mta.presentation import native_publication
    if native_publication.enabled():
        native_publication.require_mode()
        value['native_publication'] = native_publication.identity(run)
    if run.production_manifest.get('version')==3:
        from mta.presentation.operational_reports import generation
        value['derived_report_generation']=generation(run).digest
    return digest(value)


def seal_identity(publication):
    from mta.presentation.daily_preparation import roster_identity
    return digest(dict(run=str(publication.run_id), roster=roster_identity(),
        output=publication.output_digest,
        source=publication.source_digest, configuration=publication.configuration_digest,
        recipe=publication.recipe_digest, layers=publication.layers))


def bounded(value):
    if len(json.dumps(value, default=str)) > 65536:
        raise ValueError('Daily UI metadata exceeded its finite bound')
    return value


def prepare(run_id, *, expected_output_digest):
    """Explicit offline operation. Successful layers are reused, never rebuilt.

    A session advisory lock serializes preparation for this run without holding
    one transaction across all layers. Failed-layer rows roll back independently.
    """
    from django.db import connection
    from mta.presentation.daily_preparation import required_layers, prepare_layer
    if not transaction.get_autocommit():
        raise ValueError('Daily UI preparation owns its transaction boundaries')
    run = CalculationRun.objects.get(pk=run_id)
    if run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED' or run.output_digest != expected_output_digest:
        raise PublicationUnavailable('explicit_completed_daily_run_required')
    if str(run.pk) == str(settings.VF_MTA_PUBLISHED_RUN):
        raise PublicationUnavailable('selected_run_cannot_be_prepared')
    lock = int.from_bytes(run.pk.bytes[:8], 'big', signed=True)
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_try_advisory_lock(%s)', [lock])
        if not cursor.fetchone()[0]:
            raise PublicationUnavailable('daily_preparation_already_running')
    try:
        layers_required = required_layers()
        identities = dict(output_digest=run.output_digest, source_digest=source_identity(run),
            configuration_digest=configuration_identity(), recipe_digest=recipe_identity())
        publication, created = DailyUiPublication.objects.get_or_create(run=run, defaults=identities)
        # The recorded coordinator recipe identifies its original producer.
        # It is not a data-format contract and a new coordinator must not force
        # regeneration/resealing of unchanged accepted layers. Source, output,
        # configuration, finite layer roster and layer-specific readers remain
        # strict; new layer builders still issue their own typed receipts.
        if any(getattr(publication, key) != value for key, value in identities.items()
               if key != 'recipe_digest'):
            raise PublicationUnavailable('daily_publication_identity_changed')
        if publication.status == 'READY':
            require_ready(run)
            return publication
        if publication.recipe_digest != identities['recipe_digest']:
            raise PublicationUnavailable('incomplete_publication_producer_changed')
        attempt = DailyUiPublicationAttempt.objects.create(publication=publication)
        layers = dict(publication.layers)
        results = {}
        try:
            for name in layers_required:
                try:
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT set_config('fresh.daily_publication_build', %s, true)", [str(run.pk)])
                        if name in layers and layers[name].get('status') == 'READY':
                            result = layers[name]
                            verify_layer = __import__('mta.presentation.daily_preparation',
                                fromlist=['verify_layer']).verify_layer
                            verify_layer(run,name,result['receipt'])
                        else:
                            with stage('ui_layer_prepare',layer=name):
                                result = dict(status='READY', receipt=bounded(prepare_layer(run, name)))
                            summary('ui_layer_rows',layer=name,rows=result['receipt'].get('row_count',0))
                        layers[name] = result
                        # Commit the reusable identity with its sealed rows.
                        # A killed worker must not leave an undiscoverable layer.
                        publication.layers = bounded(layers)
                        publication.save(update_fields=['layers'])
                except Exception as exc:
                    result = dict(status='FAILED', error_type=type(exc).__name__, error=str(exc)[:2000])
                    # Failed builds retain their diagnostic and may be retried.
                    layers[name] = result
                results[name] = result
                attempt.layers = bounded(results)
                attempt.save(update_fields=['layers'])
            with transaction.atomic():
                publication.layers = bounded(layers)
                complete = set(layers) == set(layers_required) and all(
                    v['status']=='READY' for v in layers.values())
                publication.status = 'READY' if complete else 'INCOMPLETE'
                publication.sealed_at = timezone.now() if complete else None
                publication.seal_digest = seal_identity(publication) if complete else ''
                publication.save(update_fields=['layers','status','sealed_at','seal_digest'])
                attempt.status = 'READY' if complete else 'FAILED'
                attempt.completed_at = timezone.now()
                attempt.save(update_fields=['status','completed_at'])
        except Exception:
            attempt.status = 'FAILED'
            attempt.completed_at = timezone.now()
            attempt.save(update_fields=['status','completed_at'])
            raise
        return publication
    finally:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_unlock(%s)', [lock])


@once_per_request
def require_ready(run, *, verify_rows=False):
    from mta.presentation.daily_preparation import required_layers, verify_layer
    layers_required = required_layers()
    publication = DailyUiPublication.objects.filter(run=run, status='READY').first()
    if publication is None:
        raise PublicationUnavailable('daily_ui_publication_not_ready')
    if (publication.output_digest != run.output_digest or publication.source_digest != source_identity(run)
            or not supported_recipe(publication.recipe_digest)
            or set(publication.layers) != set(layers_required)
            or any(value.get('status') != 'READY' for value in publication.layers.values())
            or publication.seal_digest != seal_identity(publication)):
        raise PublicationUnavailable('daily_ui_publication_seal_mismatch')
    if publication.configuration_digest != configuration_identity():
        from mta.presentation import native_publication
        if native_publication.enabled():
            raise PublicationUnavailable('native_publication_configuration_changed')
        from mta.presentation.daily_activation import require_activation
        require_activation(run, publication)
    if verify_rows:
        for name in layers_required:
            verify_layer(run, name, publication.layers[name]['receipt'])
    if str(settings.VF_MTA_PUBLISHED_RUN) == str(run.pk):
        generation=publication.layers.get('btr',{}).get('receipt',{}).get('generation')
        if not generation or settings.VF_BTR_REPORTING_GENERATION != generation:
            raise PublicationUnavailable('daily_ui_btr_generation_selection_mismatch')
    return publication


def prepare_reporting_generation(run_id, *, expected_output_digest):
    """Append summary after the existing sealed roster; never rewrite its seal.

    The old coordinator recipe hashes prepare(), not this supplemental step.
    A failed summary leaves the base receipt/selection unchanged and is not READY.
    """
    from mta.presentation.report_verification import verification_scope
    with verification_scope(CalculationRun.objects.get(pk=run_id)):
        from mta.presentation.operational_reports import prepare as prepare_sources
        with stage('derived_report_publication'):
            prepare_sources(run_id,expected_output_digest=expected_output_digest)
        publication = prepare(run_id, expected_output_digest=expected_output_digest)
        if publication.status != 'READY':
            raise PublicationUnavailable('planning_summary_requires_ready_report_layers')
        from mta.presentation.planning_summary_daily import prepare as prepare_summary
        with stage('planning_summary'):
            summary_receipt = prepare_summary(publication.run)
        return publication, summary_receipt
