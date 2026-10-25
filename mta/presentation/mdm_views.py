# **DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""Existing MDM wire routes over isolated, typed application master owners."""
from decimal import Decimal, InvalidOperation
from functools import wraps
import json

from django.conf import settings
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder

from mta.mdm import drafts, families, task_reads, tasks
from mta.mdm.source import DLL, source
from mta.presentation.views import endpoint as gateway_endpoint, identity


def endpoint(method):
    """Keep source admission and response assembly in one owned generation.

    The existing session lock permits native statement commits in decisions;
    wrapping the request in a database transaction would change that contract.
    Authentication and payload checks still execute first in the gateway wrapper.
    """
    def decorate(function):
        @gateway_endpoint(method)
        @wraps(function)
        def wrapped(request, payload, *args, **kwargs):
            from mta.runtime.mdm_models import MdmSource
            from mta.mdm.supplier_revisions import source_lock
            # Native sources have no DLL digest, but use the same publication
            # lock so validation and rows stay in one source generation.
            source_id = MdmSource.objects.filter(digest=settings.VF_MDM_SOURCE_DIGEST
                ).values_list('pk', flat=True).first()
            from mta.presentation.request_scope import in_read_request
            from mta.presentation.installation_metadata import publication_configured
            if in_read_request() and publication_configured():
                from mta.presentation import scoped_selection
                from mta.presentation.context import selected_run
                from mta.presentation.report_verification import verification_scope
                if scoped_selection.enabled():
                    from mta.presentation.scoped_admission import binding
                    from mta.presentation.context import PublicationUnavailable
                    run, _ = binding()
                    if run.mdm_input_capture.source_id != source_id:
                        raise PublicationUnavailable('phase_mdm_source_binding_differs')
                else:
                    run = selected_run()
                # Reuse the existing finite certified owner proof. Enter it
                # first to retain the day-job -> source lock order used by
                # report readers and the native day boundary.
                with verification_scope(run), source_lock(source_id):
                    return function(request, payload, *args, **kwargs)
            with source_lock(source_id):
                return function(request, payload, *args, **kwargs)
        return wrapped
    return decorate


class MdmEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def response(*, data=None, record_count=None, message=None, status=200, http_status=None):
    return JsonResponse(dict(recordCount=record_count, data=data, status=status, msg=message,
        errorCount=None, error=None, conflictErrorCount=None, conflictError=None),
        status=http_status if http_status is not None else status, encoder=MdmEncoder)


@endpoint('POST')
def configuration(request, payload):
    from mta.presentation.installation_metadata import publication_configured, configuration as metadata
    if not publication_configured():
        return response(data=metadata(drafts.value(payload, 'screenType')))
    installed = source(read_only=True)
    screen = drafts.value(payload, 'screenType')
    return response(data=[row for master_id in families.installed_ids(installed, read_only=True)
        for row in (families.module(master_id).configuration(screen, source=installed)
                    if master_id == 5 else families.module(master_id).configuration(screen))])


@endpoint('POST')
def current(request, payload, *, count=False):
    installed = source(read_only=True)
    try:
        families.require_installed(installed, payload['id'], read_only=True)
        result = families.module(payload['id']).read(installed, payload, count=count)
    except (DatabaseError, KeyError, ValueError, InvalidOperation):
        # The native SQL helper catches failures and returns empty count/null data.
        result = '' if count else None
    if count:
        return response(record_count=result, message='record count', status=0, http_status=200)
    return response(record_count='', data=result)


@endpoint('POST')
def seasonality_graph(request, payload):
    installed = source(read_only=True)
    try:
        families.require_installed(installed, 10, read_only=True)
        from mta.mdm.season_current import graph
        return response(data=graph(installed, payload))
    except task_reads.TaskDenied as exc:
        return JsonResponse({'error': str(exc)}, status=403)
    except (DatabaseError, KeyError, ValueError):
        return response(status=500)


@endpoint('GET')
def all_drafts(request, payload):
    return response(data=drafts.listing(source(), identity(request)), message='Data fetched successfully')


@endpoint('GET')
def draft_count(request, payload, draft_id):
    installed = source()
    try:
        return response(record_count=drafts.count(installed, draft_id, identity(request)))
    except drafts.DraftDenied as exc:
        return JsonResponse({'error': str(exc)}, status=403)
    except (DatabaseError, ValueError):
        return response(status=500)


@csrf_exempt
def draft(request, draft_id=None):
    allowed = ('POST', 'DELETE') if draft_id is not None else ('POST', 'PUT')
    if request.method not in allowed:
        return JsonResponse({'error': 'method_not_allowed'}, status=405)

    @endpoint(request.method)
    def handle(request, payload):
        installed = source()
        actor = identity(request)
        try:
            if request.method == 'DELETE':
                return response(**drafts.delete(installed, draft_id, actor))
            if draft_id is not None:
                return response(data=drafts.details(installed, draft_id, actor, payload),
                    message='Data fetched successfully')
            return response(**drafts.write(installed, payload, actor, modify=request.method == 'PUT'))
        except drafts.DraftDenied as exc:
            return JsonResponse({'error': str(exc)}, status=403)
        except (DatabaseError, ValueError, TypeError, KeyError):
            return response(status=500)
    return handle(request)


@endpoint('POST')
def submit(request,payload,action):
    installed=source()
    try:
        master_id = drafts.value(payload, 'id')
        families.require_installed(installed, master_id)
        return JsonResponse(families.module(master_id, 'tasks').submit(installed,payload,identity(request),action),encoder=MdmEncoder)
    except task_reads.TaskDenied as exc:
        return JsonResponse({'error':str(exc)},status=403)
    except (DatabaseError,ValueError,TypeError,KeyError,IndexError,InvalidOperation):
        return JsonResponse(dict(status=500,msg=None,taskId='',errorCount=None,error=None,conflictErrorCount=None,conflictError=None),status=500)


@endpoint('GET')
def task_list(request,payload,pending=False):
    installed=source(read_only=True)
    if pending:
        return response(data=task_reads.pending_rows(installed,identity(request)),message='Data fetched successfully')
    return response(data=task_reads.status_rows(installed,identity(request)))


@endpoint('GET')
def task_count(request,payload,task_id):
    installed=source(read_only=True)
    task = task_reads.header(installed,task_id)
    if task is None:
        return response(status=204,message='Task not present')
    master_id = int(task.MasterId)
    return response(record_count=json.dumps([{'masterId':master_id,'recordcount':families.module(master_id, 'reads').count(installed,task_id,identity(request))}],separators=(',',':')))


@endpoint('POST')
def task_details(request,payload,download=False):
    installed=source(read_only=True)
    try:
        task = task_reads.header(installed,drafts.value(payload,'taskId'))
        data = None if task is None else families.module(task.MasterId, 'reads').details(installed,payload,identity(request),download=download)
        return response(data=data,status=200 if data is not None else 204)
    except task_reads.TaskDenied as exc:
        return JsonResponse({'error':str(exc)},status=403)
    except (DatabaseError,ValueError,TypeError,KeyError):
        return response(status=500)


@endpoint('POST')
def task_history(request,payload):
    installed=source(read_only=True)
    try:
        master_id = drafts.value(payload,'masterId')
        families.require_installed(installed, master_id, read_only=True)
        data=families.module(master_id, 'reads').history(installed,payload,identity(request))
        return response(data=data,message='No tasks found which is Approved/Rejected by approver' if data is None else None)
    except task_reads.TaskDenied as exc:
        return JsonResponse({'error':str(exc)},status=403)
    except (DatabaseError,ValueError,TypeError,KeyError):
        return response(status=500)


@endpoint('POST')
def history_skus(request,payload):
    installed=source(read_only=True)
    try:
        master_id = drafts.value(payload,'masterId')
        families.require_installed(installed, master_id, read_only=True)
        return response(data=families.module(master_id, 'reads').history_skus(installed,payload))
    except (DatabaseError,ValueError,TypeError,KeyError) as exc:
        return response(status=500,message='Error '+str(exc))


@endpoint('POST')
def approve(request,payload):
    installed=source()
    try:
        task = task_reads.header(installed,drafts.value(payload,'taskId'))
        if task is None:
            raise task_reads.TaskDenied('task_reviewer_required')
        return JsonResponse(families.module(task.MasterId, 'tasks').approve(installed,payload,identity(request)),encoder=MdmEncoder)
    except task_reads.TaskDenied as exc:
        return JsonResponse({'error':str(exc)},status=403)
    except (DatabaseError,ValueError,TypeError,KeyError,IndexError,InvalidOperation):
        return JsonResponse(dict(status=500,msg=None,taskId=None,errorCount=None,error=None,conflictErrorCount=None,conflictError=None),status=500)


@endpoint('DELETE')
def delete_task(request,payload):
    installed=source()
    try:
        task_id = request.GET.get('taskId')
        task_reads.require_requester(installed,task_id,identity(request))
        task = task_reads.header(installed,task_id)
        families.module(task.MasterId, 'tasks').delete(installed,task_id,identity(request))
    except task_reads.TaskDenied as exc:
        return JsonResponse({'error':str(exc)},status=403)
    except DatabaseError:
        # Native PostQuery catches the command failure; the caller returns success.
        pass
    return response(message='Task deleted successfully')
