"""Existing MDM wire routes over isolated, typed application master owners."""
from decimal import Decimal, InvalidOperation
import json

from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder

from mta.mdm import drafts, families, task_reads, tasks
from mta.mdm.source import source
from mta.presentation.views import endpoint, identity


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
    installed = source()
    screen = drafts.value(payload, 'screenType')
    return response(data=[row for master_id in families.installed_ids(installed)
        for row in families.module(master_id).configuration(screen)])


@endpoint('POST')
def current(request, payload, *, count=False):
    installed = source()
    try:
        families.require_installed(installed, payload['id'])
        result = families.module(payload['id']).read(installed, payload, count=count)
    except (DatabaseError, KeyError, ValueError, InvalidOperation):
        # The native SQL helper catches failures and returns empty count/null data.
        result = '' if count else None
    if count:
        return response(record_count=result, message='record count', status=0, http_status=200)
    return response(record_count='', data=result)


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
    installed=source()
    if pending:
        return response(data=task_reads.pending_rows(installed,identity(request)),message='Data fetched successfully')
    return response(data=task_reads.status_rows(installed,identity(request)))


@endpoint('GET')
def task_count(request,payload,task_id):
    installed=source()
    task = task_reads.header(installed,task_id)
    if task is None:
        return response(status=204,message='Task not present')
    master_id = int(task.MasterId)
    return response(record_count=json.dumps([{'masterId':master_id,'recordcount':families.module(master_id, 'reads').count(installed,task_id,identity(request))}],separators=(',',':')))


@endpoint('POST')
def task_details(request,payload,download=False):
    installed=source()
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
    installed=source()
    try:
        master_id = drafts.value(payload,'masterId')
        families.require_installed(installed, master_id)
        data=families.module(master_id, 'reads').history(installed,payload,identity(request))
        return response(data=data,message='No tasks found which is Approved/Rejected by approver' if data is None else None)
    except task_reads.TaskDenied as exc:
        return JsonResponse({'error':str(exc)},status=403)
    except (DatabaseError,ValueError,TypeError,KeyError):
        return response(status=500)


@endpoint('POST')
def history_skus(request,payload):
    installed=source()
    try:
        master_id = drafts.value(payload,'masterId')
        families.require_installed(installed, master_id)
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
