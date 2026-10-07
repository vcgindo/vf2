"""Human-approved Planning reader admission, separate from frozen publication."""
import hashlib
import inspect
import json
from pathlib import Path
from django.conf import settings
from django.db import connection, transaction
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest

RUNS = frozenset(('63c71fa7-944d-4547-a80f-2316a580d3c7',
                  '17f0eb84-7b6d-40e9-a288-9441a4d7a860'))
ROUTES = ('overview', 'grid', 'graph', 'custom')
VERSION = 'daily-planning-smoke-v1'


def enabled(run):
    return (getattr(settings, 'VF_MTA_PLANNING_EXTENSION', '') == VERSION
            and str(run.pk) in RUNS and run.kind == 'DAILY_CHAIN')


def reader_digest():
    root = Path(__file__).parent
    # Bind the new adapter and all its shared presentation dependencies. The
    # original publication still verifies its own unchanged recipe separately.
    roster=root/'daily_planning/dependencies.json'
    paths=[root/name for name in json.loads(roster.read_text()) if name != 'views.py']
    paths.extend((root/'daily_planning').glob('*.py'))
    paths.extend((roster,root/'daily_planning/origins.json'))
    files={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in sorted(paths)}
    # Bind the actual Planning route/auth envelope, not unrelated endpoints
    # later added to the shared views module (such as the approved history path).
    from mta.presentation import views
    route_sources={name:inspect.getsource(getattr(views,name)) for name in
        ('endpoint','identity','envelope','planning_overview','planning_grid',
         'planning_graph','planning_custom')}
    return digest(dict(files=files,routes=route_sources))


def values(run):
    from mta.presentation.daily_publication import require_ready, source_identity
    from mta.presentation.daily_activation import require_activation
    from mta.runtime.models import DailyUiPublication
    if not enabled(run):
        raise PublicationUnavailable('daily_planning_extension_not_enabled_for_run')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        if cursor.fetchone()[0] != 'daily_3006':
            raise PublicationUnavailable('daily_planning_extension_owned_database_required')
    require_ready(run)
    publication = DailyUiPublication.objects.get(run=run)
    activation = require_activation(run, publication)
    result = dict(publication_seal=publication.seal_digest,
        activation_digest=activation.activation_digest,
        source_digest=source_identity(run), reader_digest=reader_digest())
    result['extension_digest'] = digest(dict(version=VERSION, routes=ROUTES,
        run=str(run.pk), date=str(run.business_date), output=run.output_digest,
        permissions=activation.permissions_digest, hierarchy=activation.hierarchy_digest,
        base_recipe=publication.recipe_digest, **result))
    return result


def require(run, route):
    from mta.runtime.models import DailyPlanningExtension
    if route not in ROUTES:
        raise PublicationUnavailable('daily_planning_extension_route_not_approved')
    expected = values(run)
    saved = DailyPlanningExtension.objects.filter(publication_id=run.pk).first()
    if saved is None or any(getattr(saved, k) != v for k, v in expected.items()):
        raise PublicationUnavailable('daily_planning_extension_missing_or_changed')
    return saved


@transaction.atomic
def activate(run, *, expected_seal):
    from mta.runtime.models import DailyUiPublication, DailyPlanningExtension
    publication = DailyUiPublication.objects.select_for_update().get(run=run)
    if publication.seal_digest != expected_seal:
        raise PublicationUnavailable('daily_planning_original_seal_changed')
    expected = values(run)
    prior = DailyPlanningExtension.objects.filter(publication=publication).first()
    if prior:
        return require(run, 'overview')
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.daily_planning_extension',%s,true)", [str(run.pk)])
    return DailyPlanningExtension.objects.create(publication=publication, **expected)
