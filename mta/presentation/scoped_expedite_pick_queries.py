"""Preparation-only Expedite Pick/chart/remark relations for an accepted BPR.

Raw Pick occurrence identity stays separate from RRR display multiplicity.
No Full receipt, live selection, missing-source fallback or storage is created.
"""
from dataclasses import dataclass
import inspect
from mta.presentation import scoped_expedite_queries as ordinary
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_sources import admitted_sources
from mta.presentation.rrr_sql import equal,key
from mta.runtime.relational_state import quote
from mta.serialization import digest

GRID_ORDER=('fact_ordinal','standard_ordinal','sku_description_ordinal','location_description_ordinal',
    'parent_description_ordinal','sku_ordinal','location_ordinal','pair_ordinal','master_ordinal')
NMS='closing/consumer_context/NMSAllItems'


def recipe_digest():
    return digest(dict(schema='fresh-bpr-expedite-pick-query-v1',
        source=inspect.getsource(inspect.getmodule(recipe_digest)),ordinary=ordinary.recipe_digest()))


@dataclass(frozen=True)
class ExpeditePickQueries:
    prepared: object
    pick: object

    def provenance(self,*,parent_transit=False):
        identity=dict(schema='fresh-bpr-expedite-pick-query-v1',recipe_digest=recipe_digest(),
            report_digest=self.prepared.reports.generation.digest,pick=self.pick.provenance())
        if parent_transit:
            identity.update(source_projection_digest=self.prepared.projection.digest,
                nms=self.prepared.sources.provenance(NMS),remarks=self._remarks().provenance())
        return identity

    def prepost_members(self):
        pick,params=self.pick.pick_query()
        return ('WITH P AS ('+pick+'), children AS ('
            'SELECT '+key('"ParentWhCode"')+' AS location_key,count(*)::bigint AS multiplicity FROM P '
            'WHERE "ParentWhCode" IS NOT NULL GROUP BY '+key('"ParentWhCode"')+') '
            'SELECT S.vf_source_ordinal AS scope_ordinal,T.vf_source_ordinal AS fact_ordinal,C.multiplicity '
            'FROM P S JOIN children C ON '+key('S."WhCode"')+'=C.location_key '
            'JOIN P T ON '+equal('S."SKUCode"','T."SKUCode"')+' AND '+equal('S."WhCode"','T."WhCode"')+
            ' WHERE T."WhCode" IS NOT NULL AND T."ParentWhCode" IS NOT NULL AND NOT '+equal('T."WhCode"','T."ParentWhCode"')),params

    def chart_pick_query(self):
        pick,params=self.pick.pick_query();post,pp=self.prepared.fact_query('PickPost')
        return ('SELECT K.*,Z."PostPipelineInventoryColor" FROM ('+pick+') K JOIN ('+post+') Z '
            'ON Z.ordinal=K.vf_source_ordinal'),[*params,*pp]

    def _remarks(self):
        from mta.presentation.scoped_remarks import RemarkBinding
        remarks=self.prepared.remarks;sources=self.prepared.sources
        if not isinstance(remarks,RemarkBinding):raise PublicationUnavailable('expedite_parent_remark_binding_required')
        locator=remarks.provenance()
        if (remarks.run.pk!=sources.run.pk or locator.get('run_id')!=str(sources.run.pk)
                or locator.get('phase_id')!=str(sources.acceptance_id)
                or locator.get('phase_digest')!=sources.acceptance_digest
                or locator.get('input_digest')!=sources.run.input_digest
                or locator.get('input_manifest_digest')!=sources.run.input_manifest_digest):
            raise PublicationUnavailable('expedite_parent_remark_owner_differs')
        return remarks

    def parent_base_query(self):
        nms,params=self.prepared.image_query(NMS);remarks,rp=self._remarks().query()
        return ('WITH N AS ('+nms+'),R AS ('+remarks+') SELECT '
            'row_number() OVER (ORDER BY N.vf_ordinal,R.vf_ordinal NULLS FIRST)-1 AS ordinal,'
            'N.vf_ordinal AS nms_ordinal,R.vf_ordinal AS remark_ordinal,'
            'N."SKUCode" AS sku_code,N."WhCode" AS location_code,'
            +key('N."SKUCode"')+' AS sku_key,'+key('N."WhCode"')+' AS location_key,'
            'N."RLT" AS rlt,R."Remark" AS remark,'+key('R."Remark"')+' AS remark_key '
            'FROM N LEFT JOIN R ON '+equal('N."SKUCode"','R."SKUCode"')+
            ' AND '+equal('N."WhCode"','R."WhCode"')),[*params,*rp]

    def parent_grids_query(self):
        """Original per-branch source ordinals, before permissions/pagination."""
        parts=[];params=[]
        for branch in ('dispatch','availability'):
            sql,values=ordinary.grid_occurrences(self.pick.sources.run,'parent',branch,read_binding=self.prepared)
            parts.append("SELECT 'parent'::text AS direction,%s::text AS branch,"
                'row_number() OVER (ORDER BY '+','.join(quote(f)+' NULLS FIRST' for f in GRID_ORDER)+')-1 AS ordinal,'
                'fact_ordinal FROM ('+sql+') occurrences')
            params.extend([branch,*values])
        return ' UNION ALL '.join(parts),params

    def parent_match_query(self):
        grids,gp=self.parent_grids_query();remarks,rp=self._remarks().query()
        pick,pp=self.pick.pick_query();base,bp=self.parent_base_query()
        facts,fp=self.prepared.fact_query('ExpediteDispatches')
        return ('WITH G AS ('+grids+'),R AS ('+remarks+'),P AS ('+pick+'),'
            'B AS (SELECT %s::uuid AS run_id,base.* FROM ('+base+') base),A AS ('+facts+'), candidates AS (SELECT '
            'B.ordinal AS base_ordinal,G.branch,G.ordinal AS grid_ordinal,'
            'P.vf_source_ordinal AS pick_ordinal,P."ParentStockForRationing" AS parent_stock '
            'FROM B JOIN R ON R.vf_ordinal=B.remark_ordinal '
            'JOIN A ON A.run_id=B.run_id AND '+equal('A."SKUCode"','R."SKUCode"')+' AND '+equal('A."WhCode"','R."WhCode"')+
            " JOIN G ON G.direction='parent' AND G.fact_ordinal=A.ordinal "
            'LEFT JOIN P ON '+equal('P."SKUCode"','A."SKUCode"')+' AND '+equal('P."WhCode"','A."WhCode"')+' WHERE B.run_id=%s) '
            'SELECT row_number() OVER (ORDER BY base_ordinal,branch,grid_ordinal,pick_ordinal NULLS FIRST)-1 AS ordinal,'
            'base_ordinal,branch,grid_ordinal,pick_ordinal,parent_stock FROM candidates'),[
                *gp,*rp,*pp,self.pick.run_id,*bp,*fp,self.pick.run_id]


def bind(run,*,read_binding,pick_binding):
    from mta.presentation.scoped_pick_storage import PickBinding
    if read_binding is None:raise PublicationUnavailable('expedite_scoped_binding_required')
    admitted_sources(run,read_binding=read_binding)
    if not isinstance(pick_binding,PickBinding):raise PublicationUnavailable('expedite_raw_pick_binding_required')
    report=read_binding.reports.generation;pick=pick_binding.generation;sources=read_binding.sources
    if (pick.run_id!=run.pk or sources.run.pk!=run.pk or pick_binding.sources.run.pk!=run.pk
            or report.phase_id!=sources.acceptance_id or report.phase_id!=pick.phase_id
            or report.action_revision!=pick.action_revision or report.source_digest!=pick.source_digest
            or report.configuration_digest!=pick.configuration_digest
            or sources.acceptance_id!=pick_binding.sources.acceptance_id
            or sources.acceptance_digest!=pick_binding.sources.acceptance_digest
            or sources.snapshot_digest!=pick_binding.sources.snapshot_digest
            or sources.source_digest!=pick_binding.sources.source_digest):
        raise PublicationUnavailable('expedite_raw_pick_owner_differs')
    return ExpeditePickQueries(read_binding,pick_binding)
