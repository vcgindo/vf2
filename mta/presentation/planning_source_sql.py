"""One-time Planning source SELECTs, never engine execution or HTTP joins.

These expressions feed separately sealed presentation outputs. They must not be
registered as imported images. Source ordinals identify occurrences, not a new
business key or an invented legacy report ordering.
"""
from mta.presentation.rrr_sql import equal
from mta.runtime.relational_state import quote


BPR_FIELDS = ('SKUCode', 'WHCode', 'Norm', 'ParentWhCode', 'SKUIntroDate')
GIT_FIELDS = ('Status', 'SKUCode', 'WhCode', 'Tags', 'ParentWhCode', 'Norm',
              'VirtualNorm', 'Stock', 'Git', 'PhysicalInventoryPen',
              'PhysicalInventoryColor', 'PipelineInventoryPen',
              'PipelineInventoryColor', 'Req', 'Price', 'IsParent', 'IsReceiving')


def recipe_digest():
    from mta.presentation.rrr_sql import key
    from mta.serialization import digest
    return digest(dict(version=1, bpr=bpr_master_query('MASTER'),
                       git=git_master_query('RATIONED', 'STANDARD'),
                       key=key('SOURCE'), bpr_fields=BPR_FIELDS, git_fields=GIT_FIELDS))


def source_queries(run):
    """Bind preparation SELECTs to the existing admitted fixture images.

    The preparation caller owns the transaction, source receipt and sealing.
    No API handler should call this function to reconstruct these stable bags.
    """
    from mta.presentation import fixture
    from mta.presentation.selective import image_query
    from mta.presentation.context import PublicationUnavailable
    if getattr(run, 'kind', None) == 'DAILY_CHAIN':
        from mta.presentation.daily_preparation import source_digest as daily_source_digest
        source_digest = daily_source_digest(run)
    else:
        selected, source_digest = fixture.binding()
        if (getattr(run, 'kind', None) != 'LEGACY_UI_FIXTURE' or
                selected.pk != run.pk or str(run.business_date) != '2026-04-07'):
            raise PublicationUnavailable('planning_preparation_requires_retained_april_fixture')
    master, master_params = image_query(run, 'closing/importer/MasterData')
    rationed, rationed_params = image_query(run, 'reports/bpr/vf_RationedReqReport')
    standard, standard_params = image_query(run, 'closing/dbm/SKULocStandardAttributes')
    return source_digest, {
        'bpr_master': (bpr_master_query(master), master_params, BPR_FIELDS),
        'git_master': (git_master_query(rationed, standard),
                       rationed_params + standard_params, GIT_FIELDS),
    }


def bpr_master_query(source_query):
    """01. ImportData.sql: preserve every importer occurrence and target types."""
    return ('WITH source AS (' + source_query + ') SELECT vf_ordinal source_ordinal,'
            '"SKUCode","WhCode" AS "WHCode","Norm"::integer AS "Norm",'
            '"ParentWhCode","SKUIntroDate"::date AS "SKUIntroDate" FROM source')


def git_master_query(rationed_query, standard_query):
    """GenerateGoodsInTransitMaster.sql INSERT plus existence-only flag update.

    SQL Server decimal-to-int assignment truncates, whereas PostgreSQL's numeric
    integer cast rounds: truncate Price explicitly before the bounded int cast.
    Target lengths are checked by the loader, not silently shortened here.
    """
    source = [('Status', "''::text")]
    source += [(name, 'a.' + quote(name)) for name in ('SKUCode', 'WhCode')]
    source += [('Tags', 'b."Tags"'), ('ParentWhCode', 'a."ParentWhCode"')]
    source += [(name, 'a.' + quote(name) + '::integer')
               for name in ('Norm', 'VirtualNorm', 'Stock')]
    source += [('Git', 'a."GIT"::integer'),
               ('PhysicalInventoryPen', 'a."PhysicalInventoryPen"::numeric(10,2)'),
               ('PhysicalInventoryColor', 'a."PhysicalInventoryColor"'),
               ('PipelineInventoryPen', 'a."DispatchPen"::numeric(10,2)'),
               ('PipelineInventoryColor', 'a."DispatchColor"'),
               ('Req', 'a."Req"::integer'), ('Price', 'trunc(b."Price")::integer')]
    selected = ','.join(expression + ' AS ' + quote(name) for name, expression in source)
    return ('WITH a AS (' + rationed_query + '),b AS (' + standard_query + '),'
            'base AS (SELECT a.vf_ordinal rationed_ordinal,b.vf_ordinal standard_ordinal,'
            + selected + ' FROM a JOIN b ON ' + equal('a."SKUCode"', 'b."SKUCode"')
            + ' AND ' + equal('a."WhCode"', 'b."WhCode"') + ' WHERE a."GIT">0) '
            'SELECT p.*,EXISTS(SELECT 1 FROM base c WHERE '
            + equal('p."SKUCode"', 'c."SKUCode"') + ' AND '
            + equal('p."WhCode"', 'c."ParentWhCode"')
            + ') AS "IsParent",TRUE AS "IsReceiving" FROM base p')


def validate_target_lengths(rows, fields):
    """Reject source strings that canonical target insertion would reject."""
    limits = {name: (10 if name.endswith('Color') else 50) for name in fields
              if name in ('Status', 'SKUCode', 'WHCode', 'WhCode', 'Tags',
                          'ParentWhCode', 'PhysicalInventoryColor', 'PipelineInventoryColor')}
    for row in rows:
        for name, limit in limits.items():
            value = row[name]
            # SQL nvarchar length is UTF-16 code units, not Unicode code points.
            if value is not None and len(value.encode('utf-16-le')) // 2 > limit:
                raise ValueError('Planning canonical target length exceeded: ' + name)
