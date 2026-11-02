# **DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""Pre-fork startup admission; retain identity only, never publication rows.

Qualified protected native publications admit through bounded metadata checks;
other modes retain the full audit. A changed identity fails closed until a new
MTA master startup admits it. Full offline verification remains available.
Existing readers still own their row checks and complete command integrity.
"""
import hashlib
import logging
from pathlib import Path

from django.conf import settings
from django.db import InterfaceError, OperationalError, connections
from django.http import JsonResponse

from mta.presentation.context import (
    PublicationUnavailable, permission_catalogue, selected_run,
)
from mta.runtime.models import (
    PickProjection, ExcessProjection, FulfillmentProjection,
    ExpediteProjection, PickPostProjection,
)
from mta.serialization import digest
from mta.presentation.report_verification import report_operation

logger = logging.getLogger(__name__)
_admitted = None


def prepared(run):
    """Read the prepared generation identities without auditing accepted facts."""
    from mta.presentation.daily_publication import require_ready
    from mta.presentation.native_publication import identity
    from mta.presentation.accepted_publication import _summary_ready
    require_ready(run)
    _summary_ready(run)
    return identity(run)

# Only projections consumed by the routes already implemented in this build.
# Missing future BOR/MDM/logistics consumers are not admission prerequisites.
PROJECTIONS = (PickProjection, ExcessProjection, FulfillmentProjection,
               ExpediteProjection, PickPostProjection)
CONFIG_SETTINGS = (
    'VF_MTA_PUBLISHED_RUN', 'VF_MTA_PUBLISHED_DIGEST',
    'VF_MTA_NATIVE_PUBLICATION', 'VF_MTA_SELECTION_FILE', 'VF_MTA_SELECTION',
    'VF_MTA_PERMISSIONS_FILE', 'VF_MTA_PERMISSIONS_SHA256',
    'VF_MTA_HIERARCHY_FILE', 'VF_MTA_HIERARCHY_SHA256',
    'VF_MTA_TERMINAL_FILE', 'VF_MTA_TERMINAL_SHA256',
    'VF_MTA_EXCESS_HISTORY_FILE', 'VF_MTA_EXCESS_HISTORY_SHA256',
    'VF_MTA_ACTIONS_ENABLED', 'VF_MTA_ACTION_TIME_ZONE',
)


def binding(run=None):
    from mta.presentation import scoped_selection
    if scoped_selection.enabled():
        from mta.presentation.scoped_admission import binding as phase_binding
        return phase_binding(run)
    run, identity = native_binding(run)
    if getattr(settings, 'VF_BTR_REPORTING_GENERATION', ''):
        from mta.presentation.btr_reporting import admission_identity
        identity = digest(dict(native=identity, btr=admission_identity(run)))
    return run, identity


def native_binding(run=None):
    """Bounded metadata/file identity; no operational rows or input snapshot."""
    if run is None:
        run = selected_run()
    configuration = {name: getattr(settings, name) for name in CONFIG_SETTINGS}
    files = list((Path(__file__).resolve().parents[1] / 'config').glob('*.json'))
    files += [Path(configuration[name]) for name in ('VF_MTA_PERMISSIONS_FILE', 'VF_MTA_HIERARCHY_FILE', 'VF_MTA_TERMINAL_FILE') if configuration[name]]
    if configuration['VF_MTA_EXCESS_HISTORY_FILE']:
        files.append(Path(configuration['VF_MTA_EXCESS_HISTORY_FILE']))
    hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    projections = {}
    for model in PROJECTIONS:
        fields = [f.attname for f in model._meta.fields if f.name not in ('id', 'run')]
        projections[model.__name__] = list(model.objects.filter(run=run).values(*fields))
    value = dict(version=1, run_id=str(run.pk), business_date=str(run.business_date), input_digest=run.input_digest, output_digest=run.output_digest, production_digest=run.production_digest, parity_digest=digest(run.parity_summary), manifest_digest=digest(run.production_manifest), output_roster=run.output_roster, checkpoints=list(run.checkpoints.order_by('name').values('name', 'digest', 'row_count')), configuration=configuration, files=hashes, projections=projections)
    if configuration['VF_MTA_EXCESS_HISTORY_FILE'] or configuration['VF_MTA_EXCESS_HISTORY_SHA256']:
        from mta.presentation.excess_history import selected_manifest, admission_identity
        value['excess_history'] = admission_identity(run, selected_manifest(run))
    return (run, digest(value))


@report_operation
def verify(run):
    """Reuse native readback and the existing consumer validators once."""
    if getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False):
        from mta.presentation.daily_publication import require_ready
        require_ready(run, verify_rows=True)
        from mta.presentation import native_publication
        if native_publication.enabled():
            native_publication.require_mode()
            native_publication.identity(run, verify_rows=True)
            from mta.presentation.planning_summary_daily import require_ready as require_summary
            require_summary(run, verify_rows=True)
    verify_native(run)


@report_operation
def verify_native(run):
    """Existing native readback/projection checks, also before access activation."""
    from mta.runtime.services import read_outputs
    from mta.runtime.temporal import command_state
    from mta.presentation import hierarchy
    from mta.presentation.terminal_supplement import terminal_ancillary
    from mta.presentation.planning_read import terminal_git_reports
    from mta.presentation.pick_storage import read_pick_bands
    from mta.presentation.excess_storage import read_excess
    from mta.presentation.fulfillment_storage import read_fulfillment
    from mta.presentation.expedite_storage import read_expedite
    from mta.presentation.pick_post_storage import read_pick_post

    from mta.presentation.native_publication import enabled
    if enabled() and run.production_manifest.get('version') in (2, 3):
        from mta.presentation.report_verification import consumer_outputs
        output = consumer_outputs(run)
    else:
        output = read_outputs(run)
    dbm, _ = command_state(run, output['DBMFinal'][0])
    catalogue = permission_catalogue()
    manifest = hierarchy.selected_manifest(run)
    if manifest:
        hierarchy.project(output, dbm, catalogue, manifest)
    # No opt-in retains native NULL-denial / unavailable ancillary behavior.
    if settings.VF_MTA_TERMINAL_FILE or settings.VF_MTA_TERMINAL_SHA256:
        ancillary = terminal_ancillary(run)
        terminal_git_reports(output['BPRReports'][0]['vf_RationedReqReport'], ancillary)
        if any(row['GIT'] != 0 for row in output['BPRReports'][0]['BPR_Table']):
            raise PublicationUnavailable('terminal_empty_transit_conflicts_with_published_git')
    bands = read_pick_bands(run)
    read_excess(run, output=output)
    read_fulfillment(run, output=output)
    read_expedite(run, output=output, bands=bands)
    read_pick_post(run, output=output, bands=bands)
    if settings.VF_MTA_EXCESS_HISTORY_FILE or settings.VF_MTA_EXCESS_HISTORY_SHA256:
        from mta.presentation.excess_history import selected_manifest, read_history
        read_history(run, selected_manifest(run))
    # All local row objects are released on return. No result cache is retained.


def admit():
    """Startup only. A failed attempt never leaves an older admission active."""
    global _admitted
    from mta.presentation.identity_reuse import clear
    clear()
    _admitted = None
    from mta.presentation import scoped_selection
    if scoped_selection.enabled():
        from mta.presentation.scoped_admission import startup
        run, after, reference = startup()
        _admitted = after
        return dict(run_id=str(run.pk), business_date=str(run.business_date),
            output_digest=run.output_digest, admission_digest=after,
            validation='accepted_phase_metadata', phase='BPR', phase_read_reference=reference)
    from mta.presentation.accepted_publication import startup
    accepted = startup(binding)
    bounded = accepted is not None
    if bounded:
        run, after = accepted
    else:
        run, before = binding()
        verify(run)
        if getattr(settings, 'VF_BTR_REPORTING_GENERATION', ''):
            from mta.presentation.btr_reporting import selected_generation, verify_generation
            verify_generation(selected_generation(run))
        _, after = binding()
        if before != after:
            raise PublicationUnavailable('publication_changed_during_admission')
    _admitted = after
    result = dict(run_id=str(run.pk), business_date=str(run.business_date),
                  output_digest=run.output_digest, admission_digest=after,
                  validation='accepted_metadata' if bounded else 'full_audit')
    if getattr(settings, 'VF_BTR_REPORTING_GENERATION', ''):
        result['btr_reporting_generation'] = settings.VF_BTR_REPORTING_GENERATION
    return result


def require_admission():
    """Fail closed on changed identity; do not revalidate inside a request."""
    global _admitted
    if _admitted is None:
        raise PublicationUnavailable('publication_not_admitted')
    try:
        _, current = binding()
        if current != _admitted:
            raise PublicationUnavailable('publication_admission_changed_restart_required')
    except (OperationalError, InterfaceError):
        # Reject this request while the database is unavailable. The identity
        # was not disproved; recovery must still compare it before serving.
        # Do not permanently poison just one of the pre-admitted workers.
        raise
    except Exception:
        from mta.presentation.identity_reuse import clear
        clear()
        _admitted = None
        raise
    return _admitted


class AdmittedApplication:
    """The production WSGI boundary; direct offline proof commands are unchanged."""
    def __init__(self, application):
        from release.native_identity import require_current
        require_current()
        from mta.presentation.native_mode import require_configuration
        require_configuration()
        self.application = application
        from mta.presentation import scoped_selection
        # The new isolated shell can start before its first synthetic day exists.
        # Only a completely absent identity is allowed; a malformed, rejected or
        # partially configured selection must still abort startup as before.
        if (not scoped_selection.enabled()
                and getattr(settings, 'VF_MTA_ALLOW_UNSELECTED_STARTUP', False)
                and getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False)
                and not settings.VF_MTA_PUBLISHED_RUN and not settings.VF_MTA_PUBLISHED_DIGEST
                and not getattr(settings, 'VF_MTA_FIXTURE_FILE', '')
                and not getattr(settings, 'VF_MTA_FIXTURE_SHA256', '')):
            global _admitted
            _admitted = None
            logger.warning('No daily publication selected; shell alive, report readiness false')
            connections.close_all()
            return
        try:
            result = admit()
            logger.warning('Publication admitted: %s', result)
        except Exception:
            logger.exception('Publication admission failed; aborting application startup')
            # Gunicorn --preload executes this before listening or forking.
            # A failed verification cannot leave a partially admitted pool.
            raise
        finally:
            connections.close_all()

    def __call__(self, environ, start_response):
        from mta.presentation import publication_binding
        path = environ.get('PATH_INFO', '')
        if publication_binding.enabled() and (path == publication_binding.BOOTSTRAP
                                               or publication_binding.report_path(path)):
            # Django middleware owns this scope through lazy body consumption.
            return self._dispatch(environ, start_response)
        from mta.presentation.request_scope import read_request
        with read_request(environ.get('PATH_INFO', '')):
            return self._dispatch(environ, start_response)

    def _dispatch(self, environ, start_response):
        if environ.get('PATH_INFO', '').startswith('/api/mta/'):
            try:
                from mta.presentation.installation_metadata import (
                    publication_configured, metadata_request, initialized_master_request, require_installation)
                if not publication_configured() and metadata_request(environ):
                    require_installation()
                elif not publication_configured() and initialized_master_request(environ):
                    if require_installation() is None:
                        raise PublicationUnavailable('mdm_source_not_selected')
                else:
                    from mta.presentation import scoped_selection
                    from mta.presentation.request_scope import admission_preflight
                    anchor = getattr(settings, 'VF_MTA_PHASE_SELECTION', None)
                    scoped_dbm = (scoped_selection.enabled() and isinstance(anchor, dict)
                                  and anchor.get('schema') == scoped_selection.DBM_SCHEMA)
                    # Binding still validates the actual pinned selection. End
                    # this metadata-only lifetime before constructing any part
                    # of the downstream response or entering a write handler.
                    with admission_preflight(enabled=scoped_dbm):
                        admitted = require_admission()
                    environ['vectorflow.admitted_publication'] = admitted
            except Exception:
                connections.close_all()
                response = JsonResponse({'error': 'publication_not_admitted'}, status=503)
                start_response('503 Service Unavailable', list(response.items()))
                return response
        return self.application(environ, start_response)
