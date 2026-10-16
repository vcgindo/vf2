"""Only the six approved missing read endpoints; commands are enabled separately."""
from django.db import DatabaseError
from django.http import JsonResponse
from mta.presentation.views import endpoint, envelope
from mta.presentation.context import selected_run, PublicationUnavailable
from mta.presentation import logistics_read as reader, logistics_live


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
