"""Read-only Guided suggestion joins at an accepted BPR or pre-BTR DBM stop.

The suggestion collection remains the predecessor's BTR output. Only the M
relation is the current revision-bound DBMMaster; no early Guided generation
or completed-run prepared receipt is invented.
"""
from copy import deepcopy
from dataclasses import dataclass

from mta.presentation import scoped_btr, scoped_dbm
from mta.presentation.context import PublicationUnavailable
from mta.presentation.guided_dbm_fields import SOURCES, FIELDS
from mta.runtime import relational_state as typed
from mta.serialization import digest


MASTER = SOURCES['M']
DESCRIPTIONS = {
    'closing/btr/SKUDescriptionTbl': {'SKUCode':'text', 'SKUDescription':'text'},
    'closing/btr/SiteDescriptionTbl': {'WHCode':'text', 'WHDescription':'text'},
}
REQUIRED = {**{path:FIELDS[owner] for owner,path in SOURCES.items()}, **DESCRIPTIONS}
TEXT_TYPES = frozenset(('nvarchar','varchar','nchar','xml','decimal','numeric','float','real'))


def _checked(path, item):
    table = '/'.join(typed.CATALOG['bindings'][path])
    if (type(item) is not dict or item.get('image') != path or item.get('table') != table
            or type(item.get('count')) is not int or item['count'] < 0
            or type(item.get('fields')) is not list or item['count'] and not item['fields']):
        raise PublicationUnavailable('guided_inherited_image_differs:' + path)
    from mta.runtime.ingestion_context import sha
    sha(item.get('digest'))
    if not item['count'] and item['digest'] != digest([]):
        raise PublicationUnavailable('guided_inherited_empty_digest_differs:' + path)
    declared = dict(typed.CATALOG['tables'][table]); seen = set()
    for field in item['fields']:
        if (not isinstance(field, (list, tuple)) or len(field) != 3
                or field[0] != field[1] or field[0] not in declared or field[0] in seen
                or field[2] not in ('str','int','float','bool')):
            raise PublicationUnavailable('guided_inherited_fields_differ:' + path)
        seen.add(field[0])
    return deepcopy(item)


def inherited_images(btr, sources, paths):
    """Resolve only declared Guided paths against the already-bound predecessor."""
    from mta.presentation import operational_reports
    images = {}; generation = None
    for path in paths:
        item = btr.predecessor.production_manifest.get('images', {}).get(path)
        if item is None:
            if generation is None:
                generation = operational_reports.generation(btr.predecessor)
                actual = dict(id=str(generation.pk), digest=generation.digest,
                    source_digest=generation.source_digest, recipe_digest=generation.recipe_digest)
                if sources.inherited_btr.locator['report_generation'] != actual:
                    raise PublicationUnavailable('guided_inherited_generation_differs')
            item = generation.metadata['images'].get(path)
        images[path] = _checked(path, item)
    return images


@dataclass(frozen=True)
class GuidedDbmBinding:
    view: object
    btr: scoped_btr.BtrBinding
    context: object
    images: dict

    @property
    def run(self): return self.view.run

    def rows(self, path):
        if path == MASTER: return self.context.dbm['DBMMaster']
        if path not in self.images: raise PublicationUnavailable('guided_source_unavailable:' + path)
        return typed.load_image(self.btr.predecessor, self.images[path])

    def validate_fields(self, path):
        required = REQUIRED[path]
        if path == MASTER:
            for row in self.rows(path):
                for name, kind in required.items():
                    if name not in row or (row[name] is not None and
                            (type(row[name]) is not int if kind == 'bigint' else type(row[name]) is not str)):
                        raise PublicationUnavailable('guided_current_master_field_differs:' + name)
            return
        item = self.images[path]
        declared = dict(typed.CATALOG['tables'][item['table']])
        observed = {name:wire for name,_column,wire in item['fields']}
        for name, kind in required.items():
            physical = declared.get(name)
            if physical not in ({'int','bigint'} if kind=='bigint' else TEXT_TYPES):
                raise PublicationUnavailable('guided_source_schema_differs:' + path + '/' + name)
            if not item['count']: continue
            wire = observed.get(name)
            if wire == ('int' if kind=='bigint' else 'str'): continue
            # Same all-NULL observation exception as the existing daily
            # occurrence producer; populated text is never coerced to integer.
            if kind=='bigint' and wire=='str' and all(row[name] is None for row in self.rows(path)):
                continue
            raise PublicationUnavailable('guided_source_wire_differs:' + path + '/' + name)

    def query(self, path):
        if path not in REQUIRED: raise PublicationUnavailable('guided_source_unavailable:' + path)
        self.validate_fields(path)
        if path == MASTER:
            from mta.presentation.scoped_bor import _values
            return _values(self.rows(path), FIELDS['M'])
        item = self.images[path]
        fields = item['fields']
        selected = (','.join(typed.quote(column)+' AS '+typed.quote(name) for name,column,_ in fields)
                    if fields else ','.join(typed.quote(name) for name,_ in typed.CATALOG['tables'][item['table']]))
        return ('SELECT vf_ordinal,'+selected+' FROM '+typed.table_sql(item['table'])+
                ' WHERE vf_run_id=%s AND vf_image=%s', [self.btr.predecessor.pk, item['image']])

    def attributes(self):
        return {name:self.rows('closing/btr/'+name) for name in ('SkuAttributeData','LocationAttributeData')}

    def occurrence_query(self):
        """The daily producer's exact join/ordinal grain, without its INSERT."""
        from mta.presentation.daily_native_prepared import _raw_equal as raw_equal, DBM_ROW_FIELDS
        ctes, params = [], []
        for owner,path in SOURCES.items():
            query, values = self.query(path)
            ctes.append(owner+' AS NOT MATERIALIZED ('+query+')'); params.extend(values)
        selected = ['row_number() OVER (ORDER BY A.vf_ordinal,S.vf_ordinal,'
                    'L.vf_ordinal,P.vf_ordinal NULLS FIRST,M.vf_ordinal)-1']
        selected += [owner+'.vf_ordinal' for owner in SOURCES]
        # Match assignment to the existing prepared table's typed columns,
        # including text serialization of Weight/Volume decimal values.
        selected += [owner+'.'+typed.quote(name)+'::'+kind
                     for owner,fields in FIELDS.items() for name,kind in fields.items()]
        joins = (' FROM A JOIN S ON '+raw_equal('A."SKUCode"','S."SKUCode"')+
                 ' JOIN L ON '+raw_equal('A."WhCode"','L."WHCode"')+
                 ' LEFT JOIN P ON '+raw_equal('A."SKUCode"','P."SKUCode"')+
                 ' AND '+raw_equal('A."WhCode"','P."LocCode"')+
                 ' JOIN M ON '+raw_equal('A."SKUCode"','M."SKUCode"')+
                 ' AND '+raw_equal('A."WhCode"','M."WhCode"'))
        return ('WITH '+','.join(ctes)+' SELECT '+','.join(expression+' AS '+typed.quote(name)
                for expression,name in zip(selected,DBM_ROW_FIELDS,strict=True))+joins, params)


def bind(view):
    from mta.presentation.registered_report_view import applicable_reference
    from mta.presentation import hierarchy
    if not applicable_reference(view.reference):
        raise PublicationUnavailable('selected_guided_registered_view_required')
    try:
        if hierarchy.selected_manifest(view.run):
            raise PublicationUnavailable('guided_scoped_native_hierarchy_required')
        btr = scoped_btr.bind(view)
        sources = view.bpr.sources
        context = getattr(view, 'dbm_context', None)
        if context is None:
            context = scoped_dbm.bind(sources.acceptance_id,
                expected_digest=sources.acceptance_digest, action_revision=sources.action_revision)
        if context.run.pk != view.run_id or btr.run.pk != view.run_id:
            raise PublicationUnavailable('guided_current_owner_differs')
        images = inherited_images(btr, sources, (path for path in REQUIRED if path != MASTER))
        bound = GuidedDbmBinding(view, btr, context, images)
        for path in REQUIRED: bound.validate_fields(path)
        return bound
    except (ValueError, KeyError, TypeError, hierarchy.HierarchyUnavailable) as error:
        if isinstance(error, PublicationUnavailable): raise
        raise PublicationUnavailable('guided_scoped_source_unavailable') from error
