"""Inherited Chronic facts with current phase NMS for the existing grid join."""
from dataclasses import dataclass

from mta.presentation.context import PublicationUnavailable
from mta.presentation import scoped_btr, scoped_guided_dbm
from mta.presentation.guided_chronic_fields import SOURCES
from mta.runtime import phase_state, relational_state as typed
from mta.serialization import digest


KINDS = frozenset(('chronic-grid','chronic-loc','chronic-sku'))
FACT = SOURCES['A']
NMS = SOURCES['N']
REQUIRED = {
    FACT: {'SKUCode':'str','WhCode':'str','ParentWhCode':'str','RLT':'int','BRAge':'int',
        'PhysicalInventoryPen':'str','PhysicalInventoryColor':'str',
        'PipelineInventoryPen':'str','PipelineInventoryColor':'str','RationedQty':'int'},
    NMS: {'SKUCode':'str','WhCode':'str','SKUDescription':'str'},
    SOURCES['S']: {'SKUCode':'str'}, SOURCES['L']: {'WHCode':'str'},
    SOURCES['P']: {'SKUCode':'str','LocCode':'str'},
    **{path:{name:'str' for name in fields} for path,fields in scoped_guided_dbm.DESCRIPTIONS.items()},
}
WIRE = {**{kind:'str' for kind in scoped_guided_dbm.TEXT_TYPES},'date':'str','int':'int','bigint':'int','bit':'bool'}


@dataclass(frozen=True)
class ChronicBinding:
    view: object
    btr: scoped_btr.BtrBinding
    kind: str
    images: dict

    @property
    def run(self): return self.view.run

    def metadata(self, path):
        if path not in self.images: raise PublicationUnavailable('chronic_scoped_source_unavailable:' + path)
        item = self.images[path]
        registry = phase_state.REGISTRY if path == NMS else typed.CATALOG['tables']
        declared = dict(registry[item['table']])
        fields = item['fields']
        if not fields and not item['count']:
            if item['digest'] != digest([]):
                raise PublicationUnavailable('chronic_scoped_empty_digest_differs')
            fields = [(name,name,WIRE[kind]) for name,kind in declared.items()]
        observed = {name:wire for name,_column,wire in fields}
        if any(observed.get(name) != wire for name,wire in REQUIRED[path].items()):
            raise PublicationUnavailable('chronic_scoped_source_wire_differs:' + path)
        # Current phase queries expose logical aliases, including NMS columns.
        return dict(item,fields=[(name,name,wire) for name,_column,wire in fields])

    def rows(self, path):
        self.metadata(path)
        return (self.view.bpr.sources.rows(path) if path==NMS
                else typed.load_image(self.btr.predecessor,self.images[path]))

    def query(self, path):
        item = self.metadata(path)
        if path == NMS: return self.view.bpr.sources.query(path)
        selected = ','.join(typed.quote(column)+' AS '+typed.quote(name) for name,column,_wire in item['fields'])
        return ('SELECT vf_ordinal,'+selected+' FROM '+typed.table_sql(item['table'])+
                ' WHERE vf_run_id=%s AND vf_image=%s',[self.btr.predecessor.pk,item['image']])

    def attributes(self):
        return {name:self.rows('closing/btr/'+name) for name in ('SkuAttributeData','LocationAttributeData')}

    def occurrence_query(self):
        from mta.presentation.daily_native_prepared import _raw_equal, CHRONIC_ROW_FIELDS
        if self.kind != 'chronic-grid': raise PublicationUnavailable('chronic_grid_binding_required')
        ctes, params = [], []
        for owner,path in SOURCES.items():
            query,values=self.query(path)
            ctes.append(owner+' AS NOT MATERIALIZED ('+query+')'); params.extend(values)
        selected = ['row_number() OVER (ORDER BY A.vf_ordinal,'
            'N.vf_ordinal NULLS FIRST,L.vf_ordinal NULLS FIRST,'
            'S.vf_ordinal NULLS FIRST,P.vf_ordinal NULLS FIRST)-1']
        selected += [owner+'.vf_ordinal' for owner in SOURCES]
        selected += ['A."SKUCode"','N."SKUDescription"','A."WhCode"','A."ParentWhCode"',
            'A."RLT"','A."BRAge"','A."PhysicalInventoryPen"::text','A."PhysicalInventoryColor"',
            'A."PipelineInventoryPen"::text','A."PipelineInventoryColor"','A."RationedQty"']
        joins = (' FROM A LEFT JOIN N ON '+_raw_equal('A."SKUCode"','N."SKUCode"')+
            ' AND '+_raw_equal('A."WhCode"','N."WhCode"')+
            ' LEFT JOIN L ON '+_raw_equal('A."WhCode"','L."WHCode"')+
            ' LEFT JOIN S ON '+_raw_equal('A."SKUCode"','S."SKUCode"')+
            ' LEFT JOIN P ON '+_raw_equal('A."SKUCode"','P."SKUCode"')+
            ' AND '+_raw_equal('A."WhCode"','P."LocCode"'))
        return ('WITH '+','.join(ctes)+' SELECT '+','.join(expression+' AS '+typed.quote(name)
            for expression,name in zip(selected,CHRONIC_ROW_FIELDS,strict=True))+joins,params)


def bind(view, kind):
    from mta.presentation.registered_report_view import applicable_reference
    from mta.presentation import hierarchy
    if kind not in KINDS or not applicable_reference(view.reference):
        raise PublicationUnavailable('selected_chronic_registered_view_required')
    try:
        if hierarchy.selected_manifest(view.run):
            raise PublicationUnavailable('chronic_SQL_hierarchy_supplement_not_bound')
        btr = scoped_btr.bind(view)
        sources = view.bpr.sources
        if btr.run.pk != view.run_id:
            raise PublicationUnavailable('chronic_scoped_run_differs')
        paths = [FACT,SOURCES['S'],SOURCES['L'],SOURCES['P']]
        if kind != 'chronic-grid':
            paths.append('closing/btr/'+('SiteDescriptionTbl' if kind=='chronic-loc' else 'SKUDescriptionTbl'))
        images = scoped_guided_dbm.inherited_images(btr,sources,paths)
        if kind == 'chronic-grid':
            item = sources.metadata(NMS)
            if item['table'] != '/'.join(typed.CATALOG['bindings'][NMS]):
                raise PublicationUnavailable('chronic_current_nms_owner_differs')
            images[NMS] = item
        bound = ChronicBinding(view,btr,kind,images)
        for path in images: bound.metadata(path)
        return bound
    except (ValueError,KeyError,TypeError,hierarchy.HierarchyUnavailable) as error:
        if isinstance(error,PublicationUnavailable): raise
        raise PublicationUnavailable('chronic_scoped_source_unavailable') from error
