"""Current phase Excess plus actual own-chain observations; read-only joins."""
from dataclasses import dataclass
from datetime import timedelta

from mta.presentation import scoped_btr, native_excess_history, hierarchy
from mta.presentation.context import PublicationUnavailable
from mta.presentation.excess import FIELDS
from mta.runtime import phase_state
from mta.runtime.models import ExcessInventoryRow
from mta.runtime.relational_state import quote
from mta.serialization import digest


KINDS = frozenset(('excess-sku','excess-value'))
PATHS = tuple('closing/importer/'+name for name in
    ('SkuAttributeData','LocationAttributeData','SkuLocAttributeData'))
WIRE = {'int':'int','bigint':'int','bit':'bool','date':'str',
    **{name:'str' for name in ('nvarchar','varchar','nchar','xml','decimal','numeric','float','real')}}


@dataclass(frozen=True)
class ExcessBinding:
    view: object
    predecessor: object
    history: dict

    @property
    def run(self): return self.view.run

    def attributes(self):
        return {name:self.view.bpr.sources.rows('closing/importer/'+name)
                for name in ('SkuAttributeData','LocationAttributeData')}

    def metadata(self,path):
        if path not in PATHS: raise PublicationUnavailable('scoped_excess_source_unavailable')
        item=self.view.bpr.sources.metadata(path)
        fields=item['fields']
        if not fields and item['count']==0:
            if item['digest']!=digest([]): raise PublicationUnavailable('scoped_excess_empty_digest_differs')
            fields=[(name,name,WIRE[kind]) for name,kind in phase_state.REGISTRY[item['table']]]
        return dict(item,fields=[(name,name,wire) for name,_column,wire in fields])

    def query(self,path):
        self.metadata(path)
        return self.view.bpr.sources.query(path)

    def fact_query(self):
        current,params=self.view.bpr.reports.query('ExcessInventoryDetails')
        # These exact complete owners were admitted by native_excess_history;
        # no other run (including another day with the same date) participates.
        owners=[item['run_id'] for item in self.history['lineage']]
        prior='SELECT run_id,ordinal,'+','.join(map(quote,FIELDS))+' FROM mta.'+quote(
            ExcessInventoryRow._meta.db_table)+' WHERE run_id=ANY(%s::uuid[])'
        return ('SELECT facts.*,ordinal AS vf_ordinal FROM (('+current+') UNION ALL ('+prior+')) facts',
                [*params,owners])

    def history_query(self,cutoff):
        from mta.presentation.daily_native_prepared import _exact
        relations={}; params=[]
        for alias,path in zip(('s','l','p'),PATHS,strict=True):
            relations[alias],values=self.query(path);params.extend(values)
        facts,values=self.fact_query();params.extend(values)
        owners=[(str(self.run.pk),0)]+[(item['run_id'],item['ordinal']+1) for item in self.history['lineage']]
        owner_values=','.join(['(%s::uuid,%s::bigint)']*len(owners))
        params.extend(value for owner in owners for value in owner)
        # Preserve native history grain, exact raw equality and ordering; the
        # added current observation is a phase-owned relation, not a Full row.
        joined=('SELECT a.run_id fact_run_id,a.ordinal fact_ordinal,s.vf_ordinal sku_ordinal,'
            'l.vf_ordinal location_ordinal,p.vf_ordinal pair_ordinal,a."ReportDate" report_date,'
            'a."SKUCode" sku_code,a."WhCode" location_code,a."ParentWhCode" parent_location_code,'
            'l."LocationType" location_type,a."PhysicalInventoryColor" physical_inventory_color,'
            'a."Amount" amount,owners.source_ordinal FROM owners JOIN facts a ON a.run_id=owners.run_id '
            'JOIN s ON '+_exact('a."SKUCode"','s."SKUCode"')+
            ' JOIN l ON '+_exact('a."WhCode"','l."WHCode"')+
            ' LEFT JOIN p ON '+_exact('a."SKUCode"','p."SKUCode"')+' AND '+_exact('a."WhCode"','p."LocCode"')+
            ' WHERE a."ReportDate">%s')
        params.append(self.history['storage_cutoff'])
        sql=('WITH s AS ('+relations['s']+'),l AS ('+relations['l']+'),p AS ('+relations['p']+
            '),facts AS ('+facts+'),owners(run_id,source_ordinal) AS (VALUES '+owner_values+'),joined AS ('+joined+
            '),occurrences AS (SELECT row_number() OVER (ORDER BY report_date,source_ordinal DESC,'
            'fact_ordinal,sku_ordinal,location_ordinal,pair_ordinal NULLS FIRST)-1 ordinal,'
            'fact_run_id,fact_ordinal,sku_ordinal,location_ordinal,pair_ordinal,report_date,sku_code,'
            'location_code,parent_location_code,location_type,physical_inventory_color,amount FROM joined) '
            'SELECT * FROM occurrences WHERE report_date>%s')
        return sql,[*params,cutoff]

    def read(self,cutoff,predicate,products,locations,kind,*,minimum_age,payload):
        from mta.presentation.guided_history_prepared import read_prepared
        return read_prepared(self.run,cutoff,predicate,products,locations,kind,
            minimum_age=minimum_age,payload=payload,read_binding=self)


def bind(view):
    from mta.presentation.registered_report_view import applicable_reference
    if not applicable_reference(view.reference):
        raise PublicationUnavailable('selected_excess_registered_view_required')
    inherited=scoped_btr.bind(view)
    if (inherited.run.pk!=view.run_id or view.bpr.reports.generation.run_id!=view.run_id
            or inherited.predecessor.business_date+timedelta(days=1)!=view.run.business_date):
        raise PublicationUnavailable('scoped_excess_owner_differs')
    try:
        if hierarchy.selected_manifest(view.run):
            raise PublicationUnavailable('scoped_excess_hierarchy_not_bound')
    except hierarchy.HierarchyUnavailable as error:
        raise PublicationUnavailable(str(error)) from error
    history=native_excess_history.identity(inherited.predecessor)
    if (history['run_id']!=str(inherited.predecessor.pk) or not history['lineage']
            or history['lineage'][0]['run_id']!=history['run_id']
            or any(item['run_id']==str(view.run_id) for item in history['lineage'])):
        raise PublicationUnavailable('scoped_excess_history_owner_differs')
    bound=ExcessBinding(view,inherited.predecessor,history)
    for path in PATHS: bound.metadata(path)
    return bound
