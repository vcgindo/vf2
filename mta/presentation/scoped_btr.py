"""Inherited pre-BTR histories joined to the current accepted BPR sources.

UptoBPR stops before RunCoreBufferTrend. Its LastBatchRun date is current, but
the trend columns and BufferTrendDates retain their actual predecessor owner.
No reporting generation, current-day trend or prepared join is produced here.
"""
from copy import deepcopy
from dataclasses import dataclass

from mta.presentation.context import PublicationUnavailable
from mta.runtime import relational_state as typed

NAMES = ('BPPTrendPhysicalInv', 'BPPTrendDispatch', 'BufferTrendPhysicalInv',
    'BufferTrendDispatch', 'SkuAttributeData', 'LocationAttributeData',
    'SkuLocAttributeData', 'BufferTrendDates')
INHERITED = {**{'closing/btr/'+name: 'BTR/'+name for name in NAMES},
    'closing/consumer_context/CategoryColDescription': 'BTR/CategoryColDescription'}
CURRENT = frozenset(('reports/bpr/vf_RationedReqReport',
    'closing/dbm/SKULocStandardAttributes', 'closing/importer/SKUDescriptionTbl',
    'closing/importer/SiteDescriptionTbl'))


def _checked(path, item):
    from mta.runtime.ingestion_context import sha
    if (path not in INHERITED or type(item) is not dict or item.get('image')!=path
            or item.get('table')!=INHERITED[path] or type(item.get('count')) is not int
            or item['count']<0 or type(item.get('fields')) is not list
            or item['count'] and not item['fields']):
        raise PublicationUnavailable('btr_inherited_image_differs:'+path)
    sha(item.get('digest'))
    columns=dict(typed.CATALOG['tables'][INHERITED[path]])
    seen=set()
    for field in item['fields']:
        if (not isinstance(field,(list,tuple)) or len(field)!=3 or field[0]!=field[1]
                or field[0] not in columns or field[0] in seen
                or field[2] not in ('str','int','float','bool')):
            raise PublicationUnavailable('btr_inherited_columns_differ:'+path)
        seen.add(field[0])
    return deepcopy(item)


@dataclass(frozen=True)
class BtrBinding:
    sources: object
    predecessor: object
    images: dict

    @property
    def run(self):
        return self.sources.run

    def rows(self, path):
        if path in CURRENT:
            return self.sources.rows(path)
        if path not in self.images:
            raise PublicationUnavailable('btr_scoped_source_unavailable:'+path)
        return typed.load_image(self.predecessor,_checked(path,self.images[path]))

    def query(self, path):
        if path in CURRENT:
            return self.sources.query(path)
        if path not in self.images:
            raise PublicationUnavailable('btr_scoped_source_unavailable:'+path)
        item=_checked(path,self.images[path])
        fields=item['fields']
        selected=(','.join(typed.quote(column)+' AS '+typed.quote(name) for name,column,_ in fields)
            if fields else ','.join(typed.quote(name) for name,_ in typed.CATALOG['tables'][item['table']]))
        return ('SELECT vf_ordinal,'+selected+' FROM '+typed.table_sql(item['table'])+
            ' WHERE vf_run_id=%s AND vf_image=%s',[self.predecessor.pk,item['image']])


def bind(view):
    """Admit only the predecessor already qualified by the selected BPR view."""
    from mta.presentation import scoped_inherited_btr, operational_reports
    from mta.runtime.scoped_pick_files import _accepted
    sources=view.bpr.sources
    phase=_accepted(sources.acceptance_id,sources.acceptance_digest)
    inherited=scoped_inherited_btr.bind(phase)
    if (sources.inherited_btr is None or inherited is None
            or inherited.provenance()!=sources.inherited_btr.provenance()
            or inherited.locator['owner_kind']!='PREDECESSOR'
            or inherited.locator['representation']!='physical'
            or str(inherited.owner.pk)!=str(sources.run.predecessor_id)):
        raise PublicationUnavailable('btr_scoped_predecessor_required')
    parent=inherited.owner
    images={}
    report=None
    for path in INHERITED:
        item=parent.production_manifest.get('images',{}).get(path)
        if item is None:
            if not path.startswith('closing/btr/'):
                raise PublicationUnavailable('btr_inherited_source_unavailable:'+path)
            if report is None:
                report=operational_reports.generation(parent)
                expected=inherited.locator['report_generation']
                actual=dict(id=str(report.pk),digest=report.digest,
                    source_digest=report.source_digest,recipe_digest=report.recipe_digest)
                if expected!=actual:
                    raise PublicationUnavailable('btr_inherited_report_generation_differs')
            item=report.metadata['images'].get(path)
        images[path]=_checked(path,item)
    return BtrBinding(sources,parent,images)
