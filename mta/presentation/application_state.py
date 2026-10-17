"""Distinguish legitimate setup from an unavailable configured publication."""
import os

from django.conf import settings
from django.db import connection

from mta.presentation.context import PublicationUnavailable


class SetupRequired(PublicationUnavailable):
    def __init__(self, state):
        self.state = state
        super().__init__('business_initialization_required' if not state['initialized']
                         else 'published_operational_day_required')


def publication_configured():
    return any(getattr(settings, name, None) for name in (
        'VF_MTA_PUBLISHED_RUN', 'VF_MTA_PUBLISHED_DIGEST', 'VF_MTA_SELECTION_FILE',
        'VF_MTA_SELECTION', 'VF_MTA_FIXTURE_FILE', 'VF_MTA_FIXTURE_SHA256'))


def setup_state():
    """Validate current installation/source, with no inferred publication."""
    if publication_configured():
        raise PublicationUnavailable('configured_publication_requires_admission')
    from mta.runtime.models import CalculationRun, MdmSource, ProductionInitialization
    if CalculationRun.objects.exists():
        raise PublicationUnavailable('existing_runs_require_explicit_publication')
    counts = ProductionInitialization.objects.count(), MdmSource.objects.count()
    if counts not in ((0, 0), (1, 1)):
        raise PublicationUnavailable('inconsistent_initialization_source')
    if counts == (1, 1):
        # source() owns the actual initialization/namespace/family read checks.
        # The source digest must be explicitly supplied from its real receipt.
        from mta.mdm.source import source
        installed = source(read_only=True)
        if not ProductionInitialization.objects.filter(source=installed).exists():
            raise PublicationUnavailable('initialization_source_identity_differs')
        return dict(installed=True, initialized=True, publication_selected=False,
                    state='initialized', source_digest=installed.digest)
    if settings.VF_MDM_SOURCE_DIGEST:
        raise PublicationUnavailable('configured_mdm_source_missing')
    from mta.mdm import owned_namespace as owned
    with connection.cursor() as cursor:
        cursor.execute('SELECT to_regclass(%s)', [owned.REGISTRY])
        registered = cursor.fetchone()[0] is not None
        if registered:
            from mta.mdm.initialization import current_implementation_digest
            database = owned._database_identity(cursor)
            registration = owned._registered_identity(cursor)
            evidence = owned._catalogue_evidence(cursor, database, registration)
            owned._validate_application(cursor, database, registration, evidence,
                artifact_sha256=registration['artifact_sha256'],
                implementation_sha256=current_implementation_digest())
        else:
            from release.installed_application import require_setup_grants
            require_setup_grants(cursor,
                owner=os.environ.get('MTA_OWNER_ROLE', 'vectorflow_mta_owner'),
                runtime=settings.DATABASES['default']['USER'])
    return dict(installed=True, initialized=False, publication_selected=False,
                state='installed')


def prerequisite(state, *, population=False):
    if population and state['initialized']:
        return
    raise SetupRequired(state)
