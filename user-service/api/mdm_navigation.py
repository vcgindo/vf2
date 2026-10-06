"""Approved menu aliases for existing MTA MDM navigation grants."""

_MDM_PAGES = (
    'control-panel', 'saved-drafts', 'task-pending', 'task-status',
    'data-modification-history',
)


def with_mdm_menu_aliases(urls):
    result = set(urls)
    for page in _MDM_PAGES:
        if '/mta/master-data-management/' + page in result:
            result.add('/masters-interceptor/' + page)
    return list(result)
