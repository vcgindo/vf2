"""Finite Guided read bundle for one already admitted intermediate reference."""
from dataclasses import dataclass

from mta.presentation import (scoped_guided_dbm, scoped_guided_chronic,
    scoped_guided_availability, scoped_guided_excess)
from mta.presentation.context import PublicationUnavailable, permission_catalogue
from mta.presentation.insight_read import KINDS
from mta.serialization import digest


@dataclass(frozen=True)
class GuidedBinding:
    view: object
    suggestions: scoped_guided_dbm.GuidedDbmBinding
    chronic: dict
    availability: scoped_guided_availability.AvailabilityBinding
    excess: scoped_guided_excess.ExcessBinding

    @property
    def run(self): return self.view.run

    def identity(self,payload,actor):
        from mta.presentation.registered_report_view import recipe_digest
        catalogue=permission_catalogue()
        permissions={}
        for key,dimension in (('product_permissions','products'),('location_permissions','locations')):
            assigned=payload.get(key,[])
            if not isinstance(assigned,list) or any(isinstance(v,bool) or not str(v).isdigit() for v in assigned):
                raise ValueError('invalid_permission_scope_id')
            if {int(v) for v in assigned}-{row['id'] for row in catalogue[dimension]['records']}:
                raise PublicationUnavailable('permission_hierarchy_unavailable')
            permissions[key]=assigned
        receipt=self.availability.receipt
        # Reference owns action/remark changes even when report facts retain
        # their original build revision. Never key merely by business date.
        return dict(schema='fresh-scoped-guided-read-v1',run_id=str(self.run.pk),
            business_date=self.run.business_date.isoformat(),reference=self.view.read_identity,
            action_revision=self.view.action_revision,bpr=self.view.bpr.read_identity,
            suggestions=dict(predecessor=str(self.suggestions.btr.predecessor.pk),
                images=self.suggestions.images,current_master=digest(self.suggestions.context.dbm['DBMMaster'])),
            chronic={kind:bound.images for kind,bound in self.chronic.items()},
            availability=dict(predecessor=str(self.availability.btr.predecessor.pk),
                source=receipt.source_digest,schema=receipt.schema_digest,rows=receipt.rows_digest,
                row_count=receipt.row_count,reference_count=receipt.reference_count,
                aggregate=self.availability.aggregate),
            excess=dict(history=self.excess.history,generation=str(self.view.bpr.reports.generation.pk),
                generation_digest=self.view.bpr.reports.generation.digest),
            recipe=recipe_digest(),catalogue=digest(catalogue),permissions=permissions,actor=actor)

    def response(self,payload,kind):
        from mta.presentation import views
        from mta.presentation.insight_response import insight_payload
        if kind not in KINDS: raise ValueError('unknown_guided_insight')
        if kind in ('loc','sku','pie','ageing'):
            from mta.presentation.guided_dbm import read_guided_dbm
            values=read_guided_dbm(self.run,payload,kind,self.suggestions.attributes(),read_binding=self.suggestions)
        elif kind=='chronic-grid':
            from mta.presentation.guided_chronic import read_guided_chronic
            values=read_guided_chronic(self.run,payload,read_binding=self.chronic[kind])
        elif kind.startswith('chronic-'):
            from mta.presentation.chronic_sql import read_chronic
            values=read_chronic(self.run,payload,kind,read_binding=self.chronic[kind])
        else:
            from mta.presentation.insight_history_sql import read_history
            try:
                values=read_history(self.run,payload,kind,
                    read_binding=self.excess if kind.startswith('excess-') else self.availability)
                return views.envelope(data=views.scalar_json_rows(values))
            except OverflowError:
                if kind.startswith('excess-'): return views.envelope(status=500)
                raise
        return views.envelope(data=insight_payload(values,kind))


def bind(view):
    return GuidedBinding(view,scoped_guided_dbm.bind(view),
        {kind:scoped_guided_chronic.bind(view,kind) for kind in sorted(scoped_guided_chronic.KINDS)},
        scoped_guided_availability.bind(view),scoped_guided_excess.bind(view))
