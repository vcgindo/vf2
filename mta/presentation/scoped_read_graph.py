"""Bind an immutable report graph once, under its explicit current reference.

Every existing component validator and guard remains in force. Dependencies
flow forward as admitted objects instead of recursively re-reading the graph.
No producer, report-row copy or request-global stale-source allowance is used.
"""
from dataclasses import replace
from mta.presentation.context import PublicationUnavailable
from mta.presentation import (scoped_sources,scoped_report_storage,scoped_prepared,
    scoped_planning,scoped_transit_storage,scoped_pick_storage,scoped_git,
    scoped_expedite_storage,scoped_expedite_parent,scoped_expedite,
    scoped_remarks,scoped_requests)
from mta.runtime import models


def bind(row, *, retained_parent=False):
    report=row.report_generation
    build=report.action_revision
    sources=scoped_sources.bind(report.phase_id,expected_digest=row.metadata['phase_digest'],
        action_revision=build,include_nms=True,include_inherited_btr=True,read_reference=row)
    nms=replace(sources,inherited_btr=None)
    plain=replace(nms,_images={name:item for name,item in sources._images.items()
        if name!='closing/consumer_context/NMSAllItems'})
    scoped_report_storage.verify_guards()
    reports=scoped_report_storage._binding(report,plain,
        expected_digest=row.metadata['bpr']['report_digest'],action_revision=build)
    projection=models.ScopeSourceProjection.objects.get(generation_id=report.pk)
    scoped_prepared.verify_guards()
    scoped_prepared._verify_projection(projection,reports,
        expected_digest=row.metadata['bpr']['projection_digest'])
    prepared=scoped_prepared.PreparedBinding(projection,reports,plain)
    nms_prepared=replace(prepared,sources=nms)

    planning_row=models.ScopePlanningProjection.objects.get(generation_id=report.pk)
    scoped_planning.verify_guards()
    planning=scoped_planning._binding(planning_row,nms_prepared,
        expected_digest=row.metadata['planning']['planning_digest'],expected_report_digest=report.digest)

    locator=row.metadata['expedite']
    transit_row=models.ScopeTransitGeneration.objects.select_related('phase__snapshot').get(
        pk=locator['transit_generation_id'])
    scoped_transit_storage.verify_guards()
    transit=scoped_transit_storage._binding(transit_row,plain,
        expected_digest=locator['transit_digest'],action_revision=build)
    pick_row=models.ScopePickGeneration.objects.select_related('phase__snapshot').get(
        pk=row.metadata['pick']['generation_id'])
    scoped_pick_storage.verify_guards()
    pick=scoped_pick_storage._binding(pick_row,plain,
        expected_digest=row.metadata['pick']['digest'],action_revision=build)

    core_row=models.ScopeExpediteGeneration.objects.get(pk=locator['core_generation_id'])
    if (core_row.report_generation_id!=report.pk or core_row.report_generation_digest!=report.digest
            or core_row.source_projection_digest!=projection.digest
            or core_row.pick_generation_id!=pick.generation.pk
            or core_row.pick_generation_digest!=pick.generation.digest):
        raise PublicationUnavailable('bpr_expedite_reference_dependencies_differ')
    # Preserve the original reader's semantic Pick/Expedite admission as well
    # as its local generation identity check.
    scoped_expedite_storage.pick_queries.bind(sources.run,read_binding=nms_prepared,pick_binding=pick)
    scoped_expedite_storage.verify_guards()
    core=scoped_expedite_storage._binding(core_row,nms_prepared,pick,
        expected_digest=locator['core_digest'],action_revision=build)
    remarks=scoped_remarks.bind(sources,configuration_digest=report.configuration_digest)
    parent_row=row.expedite_parent_generation
    if retained_parent:
        old=parent_row.metadata['occurrences']['remarks'];fresh=remarks.provenance()
        if (remarks.highwater<parent_row.remark_highwater
                or {k:v for k,v in old.items() if k!='live_highwater'}
                !={k:v for k,v in fresh.items() if k!='live_highwater'}):
            raise PublicationUnavailable('bpr_expedite_refresh_prefix_owner_differs')
        remarks=replace(remarks,highwater=parent_row.remark_highwater,locator=old)
    parent=scoped_expedite_parent._admit(parent_row,core,remarks,locator['parent_digest'],build)
    expedition=scoped_expedite.require_binding(sources.run,scoped_expedite.ExpediteBinding(
        core,parent,transit,scoped_requests.bind(nms)))
    if expedition.read_identity!=locator:
        raise PublicationUnavailable('bpr_expedite_reference_differs')

    git_row=row.git_generation
    if (git_row.report_generation_id!=report.pk or git_row.report_generation_digest!=report.digest
            or git_row.source_projection_digest!=projection.digest
            or git_row.transit_generation_id!=transit.generation.pk
            or git_row.transit_generation_digest!=transit.generation.digest):
        raise PublicationUnavailable('bpr_git_reference_dependencies_differ')
    scoped_git.verify_guards()
    git=scoped_git._binding(git_row,replace(prepared,transit=transit),
        expected_digest=row.metadata['git']['digest'],action_revision=build)
    return replace(prepared,sources=sources,remarks=remarks,transit=transit),planning,git,expedition
