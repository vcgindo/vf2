"""Release metadata over a verified installation, not an operational empty result.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
import os

from django.conf import settings
from django.db import connection
from mta.presentation.context import PublicationUnavailable
from mta.presentation.request_scope import once_per_request


def publication_configured():
    return getattr(settings, 'VF_MTA_SELECTION', None) is not None or any(getattr(settings, key, '') for key in (
        'VF_MTA_PUBLISHED_RUN', 'VF_MTA_PUBLISHED_DIGEST', 'VF_MTA_SELECTION_FILE',
        'VF_MTA_FIXTURE_FILE', 'VF_MTA_FIXTURE_SHA256'))


def metadata_request(environ):
    path, method = environ.get('PATH_INFO', ''), environ.get('REQUEST_METHOD', 'GET')
    if method == 'GET' and path in (
            '/api/mta/GetEnvironmentConfiguration', '/api/mta/GetAllReports',
            '/api/mta/GetAllPermmision', '/api/mta/GetUIConfig'):
        if path.endswith('/GetUIConfig'):
            from urllib.parse import parse_qs
            values = parse_qs(environ.get('QUERY_STRING', ''))
            names = values.get('reportName', [])
            if len(names) != 1 or names[0] in ('BuyerOrderReport', 'BOR_OA'):
                return False
        return True
    return method == 'POST' and path in ('/api/mta/GetMasterUIConfiguration', '/api/mta/GetState')


def initialized_master_request(environ):
    return environ.get('REQUEST_METHOD') == 'POST' and environ.get('PATH_INFO') in (
        '/api/mta/GetMasterData', '/api/mta/GetCount', '/api/mta/GetSeasonalityDetails')


@once_per_request
def require_installation():
    from release.native_identity import require_current
    require_current()
    if publication_configured() or not getattr(settings, 'VF_MTA_ALLOW_UNSELECTED_STARTUP', False):
        raise PublicationUnavailable('publication_configuration_requires_admission')
    if (not getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False)
            or not getattr(settings, 'VF_MTA_NATIVE_PUBLICATION', False)):
        raise PublicationUnavailable('installation_metadata_requires_native_daily_mode')
    if any(getattr(settings, key, '') for key in ('VF_MTA_HIERARCHY_FILE', 'VF_MTA_HIERARCHY_SHA256')):
        raise PublicationUnavailable('hierarchy_configuration_requires_publication')
    if any(getattr(settings, key, '') for key in ('VF_MTA_PERMISSIONS_FILE', 'VF_MTA_PERMISSIONS_SHA256')):
        from mta.presentation.context import permission_catalogue
        permission_catalogue()  # Configured-but-missing/corrupt is never empty.
    try:
        from release.metadata_access import validate_read_profile
        from django.db.migrations.executor import MigrationExecutor
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('fresh_control.owned_namespace')")
            registered = cursor.fetchone()[0] is not None
            if registered:
                from mta.mdm.owned_namespace import (_database_identity, _registered_identity,
                    _catalogue_evidence, _validate_application)
                from mta.mdm.initialization import current_implementation_digest
                db = _database_identity(cursor)
                registration = _registered_identity(cursor)
                _validate_application(cursor, db, registration, _catalogue_evidence(cursor, db, registration),
                    artifact_sha256=registration['artifact_sha256'],
                    implementation_sha256=current_implementation_digest())
            else:
                validate_read_profile(cursor, os.environ.get('MTA_OWNER_ROLE', 'vectorflow_mta_owner'),
                    settings.DATABASES['default']['USER'])
            cursor.execute('SELECT (SELECT count(*) FROM mta.fresh_mta_productioninitialization),'
                           '(SELECT count(*) FROM mta.fresh_mta_mdmsource),'
                           '(SELECT count(*) FROM mta.fresh_mta_calculationrun)')
            counts = cursor.fetchone()
        executor = MigrationExecutor(connection)
        if executor.migration_plan(executor.loader.graph.leaf_nodes()):
            raise ValueError('Installation migrations are incomplete')
        source_digest = getattr(settings, 'VF_MDM_SOURCE_DIGEST', '')
        if counts == (0, 0, 0) and not source_digest:
            return None
        if counts != (1, 1, 0) or not source_digest:
            raise ValueError('Operational source/publication configuration required')
        from mta.mdm.source import source
        return source(read_only=True)
    except PublicationUnavailable:
        raise
    except Exception as exc:
        raise PublicationUnavailable('installation_metadata_unavailable') from exc


def configuration(screen):
    installed = require_installation()
    from mta.mdm import families
    ids = families.installed_ids(installed, read_only=True) if installed else sorted(families.NAMES)
    return [row for mid in ids for row in (
        families.module(mid).configuration(screen, source=installed) if mid == 5
        else families.module(mid).configuration(screen))]
