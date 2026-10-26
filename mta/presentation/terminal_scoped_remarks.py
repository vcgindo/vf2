"""Publish the retained scoped remark prefix as a terminal read source.

The original capture and append-only journal remain their owners. A bounded
source descriptor carries the accepted read cut into terminal preparations;
no remark is copied, appended, resealed or inferred from a later live prefix.
"""
from dataclasses import replace
from copy import deepcopy
from mta.serialization import digest
from mta.presentation.context import PublicationUnavailable

TABLE='scoped_final/BPRReport_RemarkDetails'
REFERENCE='4dc7abd3-6667-4c56-bd80-232cbfc4505f'
REFERENCE_DIGEST='f3325f8a20a9bd100c910d1437c4a8d11af5d5f0517c73187514313bc8b16e52'
ROWS_DIGEST='a2fb1dded89ca99e2a31520dbd42c842bef1562215222bee7d9f199df7a94e17'


def retained_prefix(fresh,locator):
    actual=fresh.provenance()
    if (locator.get('live_highwater')!=2 or fresh.highwater<2
            or {k:v for k,v in actual.items() if k!='live_highwater'}
            !={k:v for k,v in locator.items() if k!='live_highwater'}):
        raise PublicationUnavailable('terminal_scoped_remark_prefix_differs')
    bound=replace(fresh,highwater=2,locator=deepcopy(locator))
    bound.verify_rows()
    values=bound.rows()
    if len(values)!=2 or digest(values)!=ROWS_DIGEST:
        raise PublicationUnavailable('terminal_scoped_remark_rows_differ')
    return bound,values


def binding(run):
    from mta.runtime.production_post_dbm import AUTHORITY
    from mta.runtime.models import ScopeReadReference
    from mta.presentation import scoped_view,scoped_sources,scoped_remarks
    if (str(run.pk)!=AUTHORITY['run'] or run.input_digest!=AUTHORITY['input_digest']
            or run.input_manifest_digest!=AUTHORITY['input_manifest_digest']):
        raise PublicationUnavailable('terminal_scoped_remark_run_differs')
    reference=ScopeReadReference.objects.select_related('report_generation__phase').get(pk=REFERENCE)
    scoped_view.verify_guards()
    phase=reference.report_generation.phase
    if (reference.digest!=REFERENCE_DIGEST or digest(reference.metadata)!=REFERENCE_DIGEST
            or reference.recipe_digest!=scoped_view.recipe_digest()
            or reference.metadata['action_revision']!=AUTHORITY['action_revision']
            or reference.metadata['run_id']!=str(run.pk) or phase.run_id!=run.pk
            or reference.metadata['phase_id']!=str(phase.pk)
            or reference.metadata['phase_digest']!=phase.digest):
        raise PublicationUnavailable('terminal_scoped_remark_reference_differs')
    sources=scoped_sources.bind(phase.pk,expected_digest=phase.digest,action_revision=AUTHORITY['action_revision'])
    fresh=scoped_remarks.bind(sources,configuration_digest=AUTHORITY['profile_digest'])
    bound,values=retained_prefix(fresh,reference.metadata['bpr']['remarks'])
    metadata=dict(image=scoped_remarks.PATH,table=TABLE,count=len(values),digest=digest(values),
        fields=[[name,name,'str'] for name in scoped_remarks.FIELDS],
        reference_id=REFERENCE,reference_digest=REFERENCE_DIGEST,remarks=bound.provenance())
    return bound,values,metadata


def publish(run):
    from mta.runtime.production_post_dbm import AUTHORITY
    if str(run.pk)!=AUTHORITY['run']:return {}
    from mta.runtime.scoped_postdbm_recovery import _pending_owner
    from mta.runtime.models import RemarkOwner
    from mta.presentation.scoped_remarks import FAMILY,PATH
    _pending_owner(run)
    owner=RemarkOwner.objects.select_for_update().get(pk=FAMILY)
    if owner.next_ordinal!=2:
        raise PublicationUnavailable('terminal_scoped_remark_publication_cut_changed')
    _bound,_rows,metadata=binding(run)
    return {PATH:metadata}


def read(run,item,*,as_query=False):
    bound,values,metadata=binding(run)
    if item!=metadata:
        raise PublicationUnavailable('terminal_scoped_remark_publication_differs')
    return bound.query() if as_query else values
