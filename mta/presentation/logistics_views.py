"""Only the six approved missing read endpoints; commands are enabled separately."""
from django.db import DatabaseError, connection
from django.conf import settings
from django.http import JsonResponse
from mta.presentation.views import endpoint, envelope, identity
from mta.presentation.context import selected_run, PublicationUnavailable
from mta.presentation import logistics_read as reader, logistics_live, logistics_commands


@endpoint('POST')
def read(request, payload, *, operation):
    run = selected_run()
    try:
        if operation == 'count':
            return envelope(record_count=str(reader.transit_grid(run,payload,count=True)))
        function = dict(grid=reader.transit_grid, contacts=reader.contacts,
                        transit_history=reader.transit_history, requests=reader.open_requests,
                        expedite_history=reader.expedite_history)[operation]
        return envelope(data=function(run,payload))
    except reader.TargetDenied as exc:
        return JsonResponse({'error':str(exc)},status=403)
    except PublicationUnavailable:
        raise
    except DatabaseError:
        return envelope(status=500)


@endpoint('POST')
def command(request,payload,*,operation):
    expected=getattr(settings,'VF_MTA_LOGISTICS_COMMAND_DATABASE','')
    if not logistics_live.enabled() or not expected:
        return JsonResponse({'error':'logistics_commands_not_enabled'},status=403)
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        if cursor.fetchone()[0] != expected:
            return JsonResponse({'error':'logistics_command_database_mismatch'},status=403)
    run=selected_run()
    try:
        function=dict(transit=logistics_commands.submit_transit)[operation]
        result=function(run,payload,identity(request))
        return envelope(data=result,message='Data submitted successfully')
    except reader.TargetDenied as exc:
        return JsonResponse({'error':str(exc)},status=403)
    except DatabaseError:
        return envelope(status=500,message='Data was not submitted')
