"""Join sealed post-ration values by their producer's band occurrence."""
from collections import Counter
from django.db import connection
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest, storage


def verify_bag(expected, actual):
    # Membership ordinals are consumer identities, not PickPost ordinals. Compare
    # all produced columns and multiplicities before admitting that relation.
    if Counter(digest(row) for row in storage(expected)) != Counter(
            digest(row) for row in storage(actual)):
        raise PublicationUnavailable('daily_planning_pick_occurrence_mismatch')


def query(run):
    from mta.presentation.pick_post_storage import read_pick_post
    from mta.presentation.planning_expedite_transit_preparation import production_pick_query
    from mta.presentation.selective import image_rows
    from mta.runtime.models import PickPostRow, RrrPreparedMembership
    from mta.runtime.relational_state import quote
    expected = read_pick_post(run, output={'BPRFinal': [{
        'vf_RationedReqReport': image_rows(run, 'reports/bpr/vf_RationedReqReport')}]})
    native, params = production_pick_query(run)
    members = 'mta.' + quote(RrrPreparedMembership._meta.db_table)
    post = 'mta.' + quote(PickPostRow._meta.db_table)
    sql = ('WITH P AS (' + native + ') SELECT P.*, '
           'X."PostPipelineInventoryPen",X."PostPipelineInventoryColor" '
           'FROM P JOIN ' + members + ' H ON H.run_id=%s '
           'AND H.ordinal=P.vf_source_ordinal JOIN ' + post + ' X '
           'ON X.run_id=H.run_id AND X.ordinal=H.band_ordinal')
    params = [*params, run.pk]
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        fields = [column[0] for column in cursor.description]
        actual = [dict(zip(fields, row)) for row in cursor.fetchall()]
    for row in actual:
        row.pop('vf_source_ordinal')
    verify_bag(expected, actual)
    return sql, params
