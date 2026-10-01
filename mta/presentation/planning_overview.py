"""SCIH.GetQuadrantDetails: ten distinct count contracts, not grid totals.

Deployed source SHA f709a448c1bb6f6af6583975a13a88cf3cb009caee516bc2fe867af21eb624e5.
All joins retain SQL NULL exclusion and duplicate multiplicity. Only the selected
unfiltered contract is connected here; endpoint rejects active filters.
"""
from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import index, sql_key


def counts(attributes, standards, reports, business_date, *, products, locations):
    indexes = {name: index(attributes[name], *fields) for name, fields in (
        ('SKUDescriptionTbl', ('SKUCode',)), ('SiteDescriptionTbl', ('WHCode',)),
        ('SkuAttributeData', ('SKUCode',)), ('LocationAttributeData', ('WHCode',)),
        ('SkuLocAttributeData', ('SKUCode', 'LocCode')))}
    standard = index(standards, 'SKUCode', 'WhCode')
    transporter = index(reports['transporter'], 'SKUCode', 'WhCode')
    transit = index(reports['transit'], 'SKUCode', 'WhCode')

    def weight(row, location='WhCode'):
        return (permission_multiplicity(products, row['SKUCode']) *
                permission_multiplicity(locations, row[location]))

    def metadata(row, *, parent=False, with_standard=False):
        sku, loc = row['SKUCode'], row['WhCode']
        value = 1
        for table, key in (('SKUDescriptionTbl', (sku,)), ('SiteDescriptionTbl', (loc,)),
                           ('SkuAttributeData', (sku,)), ('LocationAttributeData', (loc,)),
                           ('SkuLocAttributeData', (sku, loc))):
            value *= len(indexes[table].get(sql_key(*key), []))
        if parent:
            value *= max(1, len(indexes['SiteDescriptionTbl'].get(sql_key(row['ParentWhCode']), [])))
        if with_standard:
            value *= len(standard.get(sql_key(sku, loc), []))
        return value

    def positive(value):
        return value is not None and value > 0

    critical = {sql_key('Black'), sql_key('Red')}
    git = [r for r in reports['git'] if positive(r['GIT']) and sql_key(r['PhysicalInventoryColor']) in critical]
    expedite = [r for r in reports['expedite'] if positive(r['RationedQty']) and sql_key(r['PipelineInventoryColor']) in critical]
    excess = [r for r in reports['excess'] if str(r['ReportDate']) == str(business_date)]
    git_counts = [sum(weight(r, location) * metadata(r, parent=True) *
                      max(1, len(transporter.get(sql_key(r['SKUCode'], r['WhCode']), [])))
                      for r in git) for location in ('WhCode', 'ParentWhCode')]
    git_counts.append(sum(weight(r) * len(transit.get(sql_key(r['SKUCode'], r['WhCode']), []))
                          for r in reports['transporter']))
    expedite_counts = [sum(weight(r, location) * metadata(r, parent=True, with_standard=True)
                           for r in expedite) for location in ('WhCode', 'ParentWhCode')]
    # Custom overview counts deliberately omit description/attribute joins.
    expedite_counts.append(sum(weight(r, 'ParentWhCode') for r in expedite))
    return [
        dict(category='git/wip', **dict(zip(('parentCount', 'childCount', 'custom'), map(str, git_counts)))),
        dict(category='expedite', **dict(zip(('parentCount', 'childCount', 'custom'), map(str, expedite_counts)))),
        dict(category='excessInventory', reviewCount=str(sum(weight(r) * metadata(r, parent=True) for r in excess)),
             custom=str(sum(weight(r) for r in excess))),
        dict(category='orderFulfillment', reviewCount=str(sum(weight(r) * metadata(r) for r in reports['fulfillment'])),
             custom=str(sum(weight(r) for r in reports['fulfillment']))),
    ]
