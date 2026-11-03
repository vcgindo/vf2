"""Explicit scoped Expedite reads and preparation; never selects a serving view."""
from dataclasses import dataclass,replace
from functools import cached_property
import inspect
from django.db import transaction
from django.core.exceptions import ValidationError
from mta.presentation import scoped_expedite_storage as core_storage,scoped_expedite_parent as parent_storage
from mta.presentation import scoped_requests,scoped_remarks,scoped_transit_storage
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest
from mta.presentation.request_scope import validated_read

SCHEMA='fresh-bpr-expedite-view-reference-v1'
RETAINED_RECIPE='b04467c6b14396263015c56e022936fb8b9e336595204b3a9a95cb359e9e7d00'


def recipe_digest():
    from mta.presentation import (planning_expedite_sql,planning_expedite_custom_sql,planning_expedite_chart_sql,
        planning_expedite_transit,planning_expedite_grids,planning_expedite_custom,planning_expedite_charts,
        expedite_read,expedite_charts,expedite_child_sources,planning_grid_sql,rrr_sql,excess_filters,expedite_parent)
    modules=(planning_expedite_sql,planning_expedite_custom_sql,planning_expedite_chart_sql,planning_expedite_transit,
        planning_expedite_grids,planning_expedite_custom,planning_expedite_charts,expedite_read,expedite_charts,
        expedite_child_sources,planning_grid_sql,rrr_sql,excess_filters,expedite_parent)
    return digest(dict(builder=inspect.getsource(inspect.getmodule(recipe_digest)),
        readers={m.__name__:inspect.getsource(m) for m in modules}))


def _owner(generation):
    return tuple(getattr(generation,f) for f in ('run_id','phase_id','action_revision','source_digest','configuration_digest'))


@dataclass(frozen=True)
class ExpediteBinding:
    core: object
    parent: object
    transit: object
    requests: object
    reader_recipe: str | None = None

    @property
    def run_id(self):return self.core.run_id

    @property
    def sources(self):return self.core.prepared.sources

    @property
    def read_identity(self):
        recipe=recipe_digest()
        if self.reader_recipe is not None:
            from mta.presentation.registered_read_compatibility import compatible_guard_recipe
            if not compatible_guard_recipe('scoped_expedite',self.reader_recipe,recipe):
                raise PublicationUnavailable('bpr_expedite_reference_differs')
            recipe=self.reader_recipe
        if self.parent.generation.recipe_digest==parent_storage.RETAINED_RECIPE:
            from mta.presentation.legacy_scope_read_compatibility import verify_expedite
            verify_expedite()
            recipe=RETAINED_RECIPE
        return dict(schema=SCHEMA,recipe_digest=recipe,run_id=str(self.run_id),
            phase_id=str(self.sources.acceptance_id),phase_digest=self.sources.acceptance_digest,
            snapshot_digest=self.sources.snapshot_digest,source_digest=self.sources.source_digest,
            configuration_digest=self.core.generation.configuration_digest,action_revision=self.sources.action_revision,
            core_generation_id=str(self.core.generation.pk),core_digest=self.core.generation.digest,
            parent_generation_id=str(self.parent.generation.pk),parent_digest=self.parent.generation.digest,
            transit_generation_id=str(self.transit.generation.pk),transit_digest=self.transit.generation.digest,
            requests=self.requests.provenance())

    @cached_property
    def _attributes(self):return self.core.attributes()

    def attributes(self):return self._attributes
    def query(self,name):return self.core.query(name)
    def fact_query(self,name):return self.core.fact_query(name)
    def image_query(self,path):return self.core.image_query(path)
    def pick_query(self):return self.core.pick_query()

    @cached_property
    def child_sources(self):
        from mta.presentation import logistics_live
        from mta.runtime.models import TransitLiveGeneration
        # A Full live annotation owner cannot certify a different phase image.
        # Native phase workflow integration must supply its applicable owner.
        if logistics_live.enabled() and TransitLiveGeneration.objects.filter(run_id=self.run_id).exists():
            raise PublicationUnavailable('scoped_expedite_live_transit_binding_required')
        return self.requests.rows(),self.transit.rows('InTransitData')


def require_binding(run,bound):
    from mta.presentation.scoped_requests import RequestBinding
    from mta.presentation.scoped_transit_storage import TransitBinding
    if (not isinstance(bound,ExpediteBinding) or bound.run_id!=run.pk
            or not isinstance(bound.core,core_storage.ExpediteBinding)
            or not isinstance(bound.parent,parent_storage.ParentBinding)
            or not isinstance(bound.transit,TransitBinding) or not isinstance(bound.requests,RequestBinding)):
        raise PublicationUnavailable('bpr_expedite_composite_owner_differs')
    generation=bound.core.generation;sources=bound.sources;request=bound.requests.provenance()
    if (generation.run_id!=sources.run.pk or generation.phase_id!=sources.acceptance_id
            or generation.action_revision!=sources.action_revision or generation.source_digest!=sources.source_digest
            or generation.configuration_digest!=bound.core.prepared.reports.generation.configuration_digest
            or _owner(bound.parent.generation)!=_owner(generation) or _owner(bound.transit.generation)!=_owner(generation)
            or bound.parent.generation.core_generation_id!=generation.pk
            or bound.parent.generation.core_generation_digest!=generation.digest
            or bound.parent.core.generation.pk!=generation.pk or bound.parent.core.generation.digest!=generation.digest
            or _owner(bound.parent.core.generation)!=_owner(generation)
            or bound.transit.generation.metadata.get('phase_digest')!=sources.acceptance_digest
            or bound.transit.generation.metadata.get('snapshot_digest')!=sources.snapshot_digest
            or bound.requests.sources.run.pk!=sources.run.pk
            or any(getattr(bound.requests.sources,f)!=getattr(sources,f) for f in
                ('acceptance_id','acceptance_digest','snapshot_digest','action_revision','source_digest'))
            or request.get('run_id')!=str(run.pk) or request.get('phase_id')!=str(sources.acceptance_id)
            or request.get('phase_digest')!=sources.acceptance_digest
            or request.get('source_digest')!=sources.source_digest or request.get('action_revision')!=sources.action_revision
            or request.get('input_digest')!=sources.run.input_digest
            or request.get('input_manifest_digest')!=sources.run.input_manifest_digest):
        raise PublicationUnavailable('bpr_expedite_composite_owner_differs')
    return bound


@validated_read
def _load(reference,*,retained_parent=False):
    from mta.presentation.registered_read_compatibility import compatible_guard_recipe
    if (not isinstance(reference,dict) or reference.get('schema')!=SCHEMA
            or (reference.get('recipe_digest')!=RETAINED_RECIPE
                and not compatible_guard_recipe('scoped_expedite',reference.get('recipe_digest'),recipe_digest()))):
        raise PublicationUnavailable('bpr_expedite_reference_differs')
    try:
        revision=reference['action_revision']
        if type(revision) is not int or revision<0:raise ValueError('Invalid action revision')
        if retained_parent:
            core=core_storage.bind(reference['core_generation_id'],expected_digest=reference['core_digest'],action_revision=revision)
            # Refresh recovery can follow an append without adopting an unknown
            # old owner. Only the admitted highwater may have advanced.
            row=parent_storage.models.ScopeExpediteParentGeneration.objects.get(pk=reference['parent_generation_id'])
            fresh=scoped_remarks.bind(core.prepared.sources,configuration_digest=core.generation.configuration_digest,
                expected_recipe=row.metadata['occurrences']['remarks']['recipe_digest'])
            old=row.metadata['occurrences']['remarks'];current=fresh.provenance()
            if (fresh.highwater<row.remark_highwater or
                    {k:v for k,v in old.items() if k!='live_highwater'}!={k:v for k,v in current.items() if k!='live_highwater'}):
                raise PublicationUnavailable('bpr_expedite_refresh_prefix_owner_differs')
            remarks=replace(fresh,highwater=row.remark_highwater,locator=old)
            parent=parent_storage._admit(row,core,remarks,reference['parent_digest'],revision)
        else:
            parent=parent_storage.bind(reference['parent_generation_id'],expected_digest=reference['parent_digest'],action_revision=revision)
            core=parent.core
            if str(core.generation.pk)!=reference['core_generation_id'] or core.generation.digest!=reference['core_digest']:
                raise PublicationUnavailable('bpr_expedite_reference_differs')
        transit=scoped_transit_storage.bind(reference['transit_generation_id'],expected_digest=reference['transit_digest'],action_revision=revision)
        requests=scoped_requests.bind(core.prepared.sources,expected_recipe=reference['requests']['recipe_digest'])
        bound=require_binding(core.prepared.sources.run,ExpediteBinding(core,parent,transit,requests,
            None if reference['recipe_digest']==RETAINED_RECIPE else reference['recipe_digest']))
        if bound.read_identity!=reference:raise PublicationUnavailable('bpr_expedite_reference_differs')
        return bound
    except (KeyError,TypeError,ValueError,ValidationError,parent_storage.models.ScopeExpediteParentGeneration.DoesNotExist) as error:
        raise PublicationUnavailable('bpr_expedite_reference_differs') from error


def bind(reference):return _load(reference)


@transaction.atomic
def prepare(phase_id,*,expected_digest,action_revision):
    from mta.runtime.models import CalculationRun,RunPhaseAcceptance
    from mta.presentation import scoped_sources,scoped_report_storage,scoped_prepared,scoped_pick_storage
    phase=RunPhaseAcceptance.objects.get(pk=phase_id)
    CalculationRun.objects.select_for_update().get(pk=phase.run_id)
    sources=scoped_sources.bind(phase_id,expected_digest=expected_digest,action_revision=action_revision,include_nms=True)
    scoped_requests.bind(sources)
    scoped_remarks.bind(sources,configuration_digest=phase.snapshot.manifest['references']['profile'])
    report=scoped_report_storage.prepare(phase_id,expected_digest=expected_digest,action_revision=action_revision)
    projection=scoped_prepared.prepare(report.pk,expected_report_digest=report.digest,action_revision=action_revision)
    pick=scoped_pick_storage.prepare(phase_id,expected_digest=expected_digest,action_revision=action_revision)
    core=core_storage.prepare(report.pk,expected_report_digest=report.digest,expected_source_digest=projection.digest,
        pick_generation_id=pick.pk,expected_pick_digest=pick.digest,action_revision=action_revision)
    parent=parent_storage.prepare(core.pk,expected_core_digest=core.digest,action_revision=action_revision)
    transit=scoped_transit_storage.prepare(phase_id,expected_digest=expected_digest,action_revision=action_revision)
    parent_bound=parent_storage.bind(parent.pk,expected_digest=parent.digest,action_revision=action_revision)
    bound=ExpediteBinding(parent_bound.core,parent_bound,
        scoped_transit_storage.bind(transit.pk,expected_digest=transit.digest,action_revision=action_revision),scoped_requests.bind(sources))
    return require_binding(sources.run,bound).read_identity


@transaction.atomic
def refresh_parent(reference):
    from mta.runtime.models import CalculationRun
    # Resolve the exact old immutable owner for recovery; no row reconstruction
    # or fresh source intake is allowed merely because a prefix changed.
    bound=_load(reference,retained_parent=True)
    CalculationRun.objects.select_for_update().get(pk=bound.run_id)
    bound=_load(reference,retained_parent=True)
    row=parent_storage.prepare(bound.core.generation.pk,expected_core_digest=bound.core.generation.digest,
        action_revision=bound.sources.action_revision)
    fresh=replace(bound,parent=parent_storage.bind(row.pk,expected_digest=row.digest,action_revision=bound.sources.action_revision),reader_recipe=None)
    return require_binding(bound.sources.run,fresh).read_identity
