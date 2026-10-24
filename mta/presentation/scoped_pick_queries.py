"""Raw Pick references and RRR display references have different grains.

Preparation-only queries over an exact accepted phase; no calculation, Full
receipt reuse, request-time admission or readiness is performed here.
"""
from dataclasses import dataclass
import inspect
from django.db import connection
from mta.presentation.context import PublicationUnavailable
from mta.presentation.planning_sources import admitted_sources
from mta.presentation import pick_storage,rrr_preparation
from mta.presentation.rrr_sql import equal
from mta.runtime.relational_state import quote,CATALOG
from mta.serialization import digest

PATH='sources/calculation/PickBands'
RATIONED='reports/bpr/vf_RationedReqReport'


def validate_band_rows(run,rows):
    # Reuse the original Full wire/code/shape rules without retaining another
    # full list of Django instances. The database's bigint range remains exact.
    try:
        for row in rows:
            record=pick_storage.native_rows(run,[row])[0]
            if any(not -(2**63)<=getattr(record,f)<2**63 for f in pick_storage.BAND_FIELDS):
                raise ValueError('Pick-band quantity exceeds bigint')
    except (ValueError,TypeError,KeyError,OverflowError) as error:
        raise PublicationUnavailable('scoped_pick_band_contract_differs') from error


def recipe_digest():
    return digest(dict(schema='fresh-bpr-pick-query-sources-v1',source=inspect.getsource(inspect.getmodule(recipe_digest)),
        original_wire=inspect.getsource(pick_storage.native_rows),
        membership=inspect.getsource(rrr_preparation.membership_query),
        positions=inspect.getsource(rrr_preparation.validate_positions),
        aliases=inspect.getsource(rrr_preparation.a_selections),sources=rrr_preparation.SOURCES,
        band_identities=pick_storage.IDENTITY_FIELDS,band_quantities=pick_storage.BAND_FIELDS,
        band_fields=pick_storage.FIELDS,rationed_fields=CATALOG['tables']['BPR/vf_RationedReqReport']))


@dataclass(frozen=True)
class PickQueries:
    prepared: object
    bands: tuple
    band_columns: tuple
    rationed: tuple

    def provenance(self):
        return dict(schema='fresh-bpr-pick-query-sources-v1',recipe_digest=recipe_digest(),
            run_id=str(self.prepared.run_id),source_digest=self.prepared.sources.source_digest,
            action_revision=self.prepared.sources.action_revision,
            images={path:self.prepared.sources.provenance(path) for path in
                (PATH,*(path for _alias,path in rrr_preparation.SOURCES))})

    def raw_membership_query(self):
        r,rp=self.rationed;k,kp=self.band_columns
        return ('WITH R AS ('+r+'),K AS ('+k+') SELECT K.column1 AS ordinal,'
            'K.column1 AS band_ordinal,R.vf_ordinal AS rationed_ordinal,'+
            equal('K.column3','K.column4')+' AS virtual FROM R JOIN K ON '+
            equal('R."SKUCode"','K.column2')+' AND '+equal('R."WhCode"','K.column3')),[*rp,*kp]

    def rrr_membership_query(self):
        ctes=[];params=[]
        for alias,path in rrr_preparation.SOURCES:
            query,values=self.prepared.image_query(path)
            ctes.append(alias+' AS NOT MATERIALIZED ('+query+')');params.extend(values)
        query,values=self.band_columns;ctes.append('K AS ('+query+')');params.extend(values)
        # Same original display grain; it must never replace raw Pick identity.
        from mta.presentation.rrr_sql import key
        fields=(('band_ordinal','K.column1'),('rationed_ordinal','R.vf_ordinal'),
            ('standard_ordinal','S.vf_ordinal'),('pair_ordinal','B.vf_ordinal'),
            ('sku_ordinal','C.vf_ordinal'),('location_ordinal','D.vf_ordinal'),
            ('left_pair_ordinal','sla.vf_ordinal'),('sku_key',key('R."SKUCode"')),
            ('location_key',key('R."WhCode"')),('parent_key',key('R."ParentWhCode"')),
            ('virtual',equal('K.column3','K.column4')),('dispatch_color_sequence','R."DispatchColorSequence"'),
            ('dispatch_pen','R."DispatchPen"'))
        joins=(' FROM R JOIN K ON '+equal('R."SKUCode"','K.column2')+' AND '+equal('R."WhCode"','K.column3')+
            ' JOIN S ON '+equal('R."SKUCode"','S."SKUCode"')+' AND '+equal('R."WhCode"','S."WhCode"')+
            ' JOIN B ON '+equal('R."SKUCode"','B."SKUCode"')+' AND '+equal('R."WhCode"','B."LocCode"')+
            ' JOIN C ON '+equal('R."SKUCode"','C."SKUCode"')+
            ' JOIN D ON '+equal('R."WhCode"','D."WHCode"')+
            ' LEFT JOIN B sla ON '+equal('R."SKUCode"','sla."SKUCode"')+' AND '+equal('R."WhCode"','sla."LocCode"'))
        return 'WITH '+','.join(ctes)+' SELECT '+','.join(value+' AS '+quote(name) for name,value in fields)+joins,params

    def pick_query(self,raw_membership=None):
        """Use a separately sealed raw membership when supplied by preparation."""
        r,rp=self.rationed;h,hp=raw_membership or self.raw_membership_query();k,kp=self.bands
        return ('WITH R AS ('+r+'),H AS ('+h+'),K AS ('+k+') '
            'SELECT H.ordinal AS vf_source_ordinal,'+','.join(rrr_preparation.a_selections())+
            ' FROM H JOIN R ON R.vf_ordinal=H.rationed_ordinal JOIN K ON K.ordinal=H.band_ordinal'),[*rp,*hp,*kp]


def bind(run,*,read_binding):
    if read_binding is None:raise PublicationUnavailable('scoped_pick_binding_required')
    admitted_sources(run,read_binding=read_binding)
    source=read_binding.sources
    metadata=source.metadata(PATH)
    if metadata['table']!='phase/PickBand':raise PublicationUnavailable('scoped_pick_band_owner_differs')
    rows=source.rows(PATH);validate_band_rows(run,rows)
    # Physical phase storage retains original wire strings. Convert only the
    # already-produced quantities, exactly as the existing typed Full writer.
    query,values=source.query(PATH)
    selected=['vf_ordinal AS ordinal',*map(quote,pick_storage.IDENTITY_FIELDS),
        *(quote(f)+'::bigint AS '+quote(f) for f in pick_storage.BAND_FIELDS)]
    bands=('SELECT '+','.join(selected)+' FROM ('+query+') accepted_bands',values)
    columns=('SELECT '+','.join(quote(f)+' AS column'+str(i) for i,f in enumerate(
        ('ordinal',*pick_storage.FIELDS),1))+' FROM ('+bands[0]+') typed_bands',values)
    rationed=read_binding.image_query(RATIONED)
    _validate_positions(rationed,columns)
    return PickQueries(read_binding,bands,columns,rationed)


def _validate_positions(rationed,columns):
    r,rp=rationed;k,kp=columns
    with connection.cursor() as cursor:
        cursor.execute('WITH R AS ('+r+'),K AS ('+k+'),'
            'selected AS (SELECT DISTINCT column2,column3,column4 FROM K) '
            'SELECT K.column2,K.column3 FROM selected K LEFT JOIN R ON '+
            equal('R."SKUCode"','K.column2')+' AND '+equal('R."WhCode"','K.column3')+
            ' GROUP BY K.column2,K.column3,K.column4 HAVING count(R.vf_ordinal)<>1 OR '
            '(NOT '+equal('K.column3','K.column4')+' AND bool_and('+
            equal('R."ParentWhCode"','K.column4')+') IS DISTINCT FROM TRUE)',[*rp,*kp])
        if cursor.fetchone():raise PublicationUnavailable('scoped_pick_rationed_position_or_parent_differs')
