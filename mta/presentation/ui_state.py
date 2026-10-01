"""Deployed DBM column projection and Commons layout storage, not engine state."""
from django.db import transaction

from mta.presentation.context import PublicationUnavailable
from mta.presentation.legacy_ui import DBM_UI_CONFIG
from mta.runtime.models import UserReportLayout


def dbm_columns():
    # UI_ReportConfiguration_2.0 + UI_ReportColumnTypes_2.0, independently
    # compared through UIConfigProcessor's SQL in verify_ui_contract.
    return [dict({key: value for key, value in row.items()
                  if key != 'TagID' and value is not None},
                 DataType='Number' if row['Col_Code'] in ('OldNormValue', 'NewNormValue') else 'String')
            for row in DBM_UI_CONFIG if row['Visible']]


def _selected(username, reportname, state=None):
    if not isinstance(reportname, str) or len(reportname) > 50:
        raise ValueError('layout_reportname_required_max50')
    if state is not None and not isinstance(state, str):
        raise ValueError('layout_state_must_be_text')
    username = str(username)
    # Do not port the deployed SQL injection defect or claim repaired behavior
    # as parity. Its quoted-literal branch is explicitly unavailable.
    if any("'" in value for value in (username, reportname, state or '')):
        raise PublicationUnavailable('LEG-LAYOUT-UNESCAPED-LITERAL: NOT_PARITY')
    return UserReportLayout.objects.filter(username=username, reportname=reportname)


def get_layout(username, reportname):
    values = list(_selected(username, reportname).values_list('state', flat=True))
    if not values:
        return ''  # ExecuteScalar has no row: GenericFunction returns "".
    if any(value != values[0] for value in values):
        raise PublicationUnavailable('LEG-LAYOUT-UNORDERED-DUPLICATE: NOT_PARITY')
    # An existing empty/NULL scalar instead returns null in GenericFunction.
    return values[0] or None


@transaction.atomic
def save_layout(username, reportname, state):
    rows = _selected(username, reportname, state)
    removed, _ = rows.delete()
    # C# string concatenation turns a missing/null state into an empty literal.
    UserReportLayout.objects.create(username=str(username), reportname=reportname, state=state or '')
    return str(removed + 1)  # ExecuteNonQuery sums DELETE and INSERT row counts.


@transaction.atomic
def reset_layout(username, reportname):
    removed, _ = _selected(username, reportname).delete()
    return str(removed)
