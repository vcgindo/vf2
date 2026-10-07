"""Approved read-time access for an already sealed synthetic publication.

No source rows, preparation receipts or original configuration are rewritten.
The only allowed configuration difference is the retained access catalogue and
its run-bound six-field hierarchy supplement. All other identities stay exact.
"""
from django.conf import settings
from django.db import connection, transaction
from mta.presentation.context import PublicationUnavailable, permission_catalogue
from mta.presentation import hierarchy
from mta.serialization import digest

CATALOGUE = '18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356'
EMPTY_ACCESS = dict(VF_MTA_PERMISSIONS_SHA256='', VF_MTA_HIERARCHY_SHA256='')


def access_manifest(run, *, verify_attributes=False):
    from mta.presentation.daily_preparation import roster_identity, SYNTHETIC_ROSTER
    if (run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED'
            or not settings.VF_MTA_DAILY_PUBLICATION
            or roster_identity() != SYNTHETIC_ROSTER
            or settings.VF_MTA_PERMISSIONS_SHA256 != CATALOGUE):
        raise PublicationUnavailable('daily_activation_scope_mismatch')
    catalogue = permission_catalogue()  # verifies exact bytes, not just settings
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest is None:
            raise hierarchy.HierarchyUnavailable('daily_activation_hierarchy_required')
        # Validate entity identity/conflicts against each consumed native owner.
        if verify_attributes:
            from mta.presentation.selective import image_rows
            for owner in ('importer', 'btr', 'dbm'):
                attributes = {name: image_rows(run, 'closing/' + owner + '/' + name)
                    for name in ('SkuAttributeData', 'LocationAttributeData')}
                hierarchy.project_attributes(attributes, catalogue, manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    return manifest


def native_verification_with_access(run, verify_only):
    """Native prepared rows can be checked, never built using a supplement."""
    if not verify_only or getattr(run, 'kind', None) != 'DAILY_CHAIN':
        return False
    access_manifest(run)
    return True


def values(run, publication):
    from mta.presentation.daily_publication import configuration_identity
    access_manifest(run)
    if publication.configuration_digest != configuration_identity(access=EMPTY_ACCESS):
        raise PublicationUnavailable('daily_activation_non_access_configuration_changed')
    result = dict(publication_seal=publication.seal_digest,
        configuration_digest=configuration_identity(),
        permissions_digest=settings.VF_MTA_PERMISSIONS_SHA256,
        hierarchy_digest=settings.VF_MTA_HIERARCHY_SHA256,
        layers_digest=digest(publication.layers))
    result['activation_digest'] = digest(dict(version=1, run=str(run.pk),
        date=str(run.business_date), output=run.output_digest, **result))
    return result


def require_activation(run, publication):
    from mta.runtime.models import DailyUiActivation
    expected = values(run, publication)
    activation = DailyUiActivation.objects.filter(publication=publication).first()
    if activation is None or any(getattr(activation, k) != v for k, v in expected.items()):
        raise PublicationUnavailable('daily_activation_missing_or_changed')
    return activation


def activate(run, *, expected_output_digest, expected_seal):
    from mta.runtime.models import DailyUiPublication, DailyUiActivation
    from mta.presentation.daily_publication import (source_identity, recipe_identity,
        seal_identity)
    from mta.presentation.daily_preparation import required_layers, verify_layer
    if (str(run.pk) == str(settings.VF_MTA_PUBLISHED_RUN)
            or run.output_digest != expected_output_digest
            or run.parity_summary.get('status') not in ('PASS', 'PASS_WITH_LEGACY_FLAWS')):
        raise PublicationUnavailable('explicit_unselected_accepted_daily_activation_required')
    with transaction.atomic():
        publication = DailyUiPublication.objects.select_for_update().get(run=run)
        if (publication.status != 'READY' or publication.seal_digest != expected_seal
                or publication.output_digest != run.output_digest
                or publication.source_digest != source_identity(run)
                or publication.recipe_digest != recipe_identity()
                or publication.seal_digest != seal_identity(publication)
                or set(publication.layers) != set(required_layers())
                or any(v.get('status') != 'READY' for v in publication.layers.values())):
            raise PublicationUnavailable('daily_activation_original_seal_mismatch')
        expected = values(run, publication)
        access_manifest(run, verify_attributes=True)
        for name in required_layers():
            verify_layer(run, name, publication.layers[name]['receipt'])
        if values(run, publication) != expected:
            raise PublicationUnavailable('daily_activation_access_changed_during_verification')
        prior = DailyUiActivation.objects.filter(publication=publication).first()
        if prior is not None:
            return require_activation(run, publication)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.daily_activation',%s,true)", [str(run.pk)])
        return DailyUiActivation.objects.create(publication=publication, **expected)
