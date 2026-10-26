"""Research uses current BPR membership and the authenticated prior BTR bags."""
from dataclasses import dataclass

from mta.presentation.context import PublicationUnavailable
from mta.presentation import scoped_btr
from mta.runtime import phase_state, relational_state


MASTER = 'reports/bpr/vf_RationedReqReport'
TRENDS = ('closing/btr/BufferTrendPhysicalInv', 'closing/btr/BufferTrendDispatch')
ATTRIBUTES = ('closing/btr/SkuAttributeData', 'closing/btr/LocationAttributeData')
REQUIRED = {MASTER: {'SKUCode', 'WhCode', 'ParentWhCode'},
    **{path: {'SKUCode', 'WhCode', 'ParentWhCode', 'Age', 'BRAge',
              *(f'D{i}' for i in range(1, 91))} for path in TRENDS},
    ATTRIBUTES[0]: {'SKUCode'}, ATTRIBUTES[1]: {'WHCode'}}


@dataclass(frozen=True)
class ResearchBinding:
    btr: scoped_btr.BtrBinding

    @property
    def run(self):
        return self.btr.run

    def metadata(self, path):
        if path not in REQUIRED:
            raise PublicationUnavailable('research_scoped_source_unavailable:' + path)
        if path == MASTER:
            item = self.btr.sources.metadata(path)
            declared = phase_state.REGISTRY[item['table']]
        else:
            item = scoped_btr._checked(path, self.btr.images.get(path))
            declared = relational_state.CATALOG['tables'][item['table']]
        fields = item['fields']
        names = {field[0] for field in fields} if fields else {name for name, _ in declared}
        if (not REQUIRED[path] <= names or len({field[0] for field in fields}) != len(fields)
                or item['count'] and not fields):
            raise PublicationUnavailable('research_scoped_source_fields_missing:' + path)
        # Both phase and inherited query APIs expose logical aliases. Their
        # physical storage column names are not query-visible identifiers.
        return dict(item, fields=[(name, name, kind) for name, _column, kind in fields])

    def rows(self, path):
        self.metadata(path)
        return self.btr.rows(path)

    def query(self, path):
        self.metadata(path)
        return self.btr.query(path)


def bind(view):
    from mta.presentation.registered_report_view import applicable_reference
    if not applicable_reference(view.reference):
        raise PublicationUnavailable('selected_research_registered_view_required')
    bound = ResearchBinding(scoped_btr.bind(view))
    if bound.run.pk != view.run_id:
        raise PublicationUnavailable('research_scoped_run_differs')
    # Validate missing/empty schemas even if permissions later select no rows.
    for path in REQUIRED:
        bound.metadata(path)
    return bound
