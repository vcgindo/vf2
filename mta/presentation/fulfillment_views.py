"""Deployed normal Fulfilment joins over typed persisted producer outputs."""
from itertools import product
from mta.presentation.rrr import index,sql_key


def joined_rows(output,rows):
    importer=output['ClosingState'][0]['importer']
    by_sku=index(importer['SKUDescriptionTbl'],'SKUCode')
    by_location=index(importer['SiteDescriptionTbl'],'WHCode')
    sku_attrs=index(importer['SkuAttributeData'],'SKUCode')
    loc_attrs=index(importer['LocationAttributeData'],'WHCode')
    pair_attrs=index(importer['SkuLocAttributeData'],'SKUCode','LocCode')
    result=[]
    for row in rows:
        sku,loc=sql_key(row['SKUCode']),sql_key(row['WhCode'])
        for sd,wd,sa,la,_ in product(by_sku.get(sku,[]),by_location.get(loc,[]),
                sku_attrs.get(sku,[]),loc_attrs.get(loc,[]),pair_attrs.get(sql_key(row['SKUCode'],row['WhCode']),[])):
            result.append({**row,'WHCode':row['WhCode'],'SKUName':sd['SKUDescription'],'WHName':wd['WHDescription'],
                'Requirement':row['TotalReq'],'PhysicalColor':row['PhysicalInventoryColor'],'PipelineColor':row['PipelineInventoryColor'],
                'PhysicalPen':None if row['PhysicalInventoryPen'] is None else float(row['PhysicalInventoryPen']),
                'PipelinePen':None if row['PipelineInventoryPen'] is None else float(row['PipelineInventoryPen']),
                **{f'sl{i}':sa[f'SL{i}'] for i in range(1,6)},**{f'll{i}':la[f'LL{i}'] for i in range(1,6)}})
    return result


def detail_aliases(rows):
    return [{**row,'WHCode':row['WhCode'],'IntroDate':row['Introdate']} for row in rows]
