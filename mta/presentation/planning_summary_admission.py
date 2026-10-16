"""Request-local summary admission without changing the sealed producer recipe."""
from mta.presentation.request_scope import once_per_request


@once_per_request
def require_ready(run, *, verify_rows=False):
    from mta.presentation.planning_summary_daily import require_ready as validate
    return validate(run, verify_rows=verify_rows)
