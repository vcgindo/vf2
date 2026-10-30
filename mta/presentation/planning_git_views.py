"""Bounded corrected child consumer; other existing Planning routes keep owners."""
from inspect import unwrap
from django.db import DatabaseError
from mta.presentation import views
from mta.presentation.context import selected_run, PublicationUnavailable


@views.endpoint('POST')
def planning_grid(request, payload, *, count=False):
    if payload.get('category') == 'git' and str(payload.get('type','')).lower() == 'child' and not count:
        run = selected_run()
        from mta.presentation.daily_preparation import production_branch
        if production_branch(run):
            from mta.presentation.planning_git_child import grid
            try:
                return views.envelope(data=grid(run, payload))
            except PublicationUnavailable:
                raise
            except (DatabaseError, ValueError, KeyError, TypeError) as error:
                raise PublicationUnavailable('GIT_corrected_child_query_unavailable') from error
    return unwrap(views.planning_grid)(request, payload, count=count)
