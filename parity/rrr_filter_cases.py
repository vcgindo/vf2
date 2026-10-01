"""Finite source-backed HTTP requests; NOT a new synthetic business artifact."""
from copy import deepcopy


def cases():
    base=dict(product_permissions=[71001],location_permissions=[72001],
              paginationParameter=dict(pageNumber=1,recordsPerPage=5000),filters={})
    roster=[]
    def add(name,groups=None,*,products=None,locations=None,page=None,error=False):
        payload=deepcopy(base)
        if groups:
            payload['filters']={key:dict(filters=[dict(attributeName=a,operator=op,value=value,**extra)
                for a,op,value,extra in entries]) for key,entries in groups.items()}
        if products is not None: payload['product_permissions']=products
        if locations is not None: payload['location_permissions']=locations
        if page: payload['paginationParameter']=page
        roster.append(dict(id=name,payload=payload,canonical_sql_error=error))
    def one(name,group,attribute,op,value,*,error=False,**extra):
        add(name,{group:[(attribute,op,value,extra)]},error=error)
    add('root-regression')
    add('selected-leaf',products=[71002])
    add('other-leaf',products=[71003])
    add('receiving-leaf',locations=[72003])
    add('other-location-leaf',locations=[72004])
    add('parent-leaf-empty',locations=[72002])
    add('leaf-intersection',products=[71002],locations=[72003])
    add('overlapping-permission-ids',products=[71001,71002,71001],locations=[72001,72003])
    add('page-two',page=dict(pageNumber=2,recordsPerPage=3))
    one('sku-code','productFilter','sku','equalto','337')
    one('location-code','locationFilter','location','equalto','DP010290')
    one('product-hierarchy','productFilter','p2','equalto','Selected')
    one('location-hierarchy','locationFilter','l2','equalto','Receiving')
    add('same-attribute-OR',{'productFilter':[('p2','equalto','Selected',{}),('p2','equalto','Other',{})]})
    add('cross-attribute-AND',{'productFilter':[('p2','equalto','Selected',{}),('p3','equalto','Leaf',{})],
                              'locationFilter':[('l2','equalto','Receiving',{})]})
    for op,value in (('equalto','B1 Product'),('notequalto','Missing'),('contains','_roduct'),
        ('doesnotcontain','Missing'),('startswith','B1'),('doesnotstartwith','Missing'),
        ('endswith','Product'),('doesnotendwith','Missing')):
        one('text-'+op,'customAttributeFilter','SKUAttr1',op,value)
    one('sql-like-brackets','customAttributeFilter','SKUAttr1','contains','[Pp]roduct')
    one('empty-hasvalue','customAttributeFilter','SKUAttr15','hasvalue','')
    one('empty-hasnovalue','customAttributeFilter','SKUAttr15','hasnovalue','')
    one('raw-null-hasnovalue','customAttributeFilter','SKULocAttr15','hasnovalue','')
    one('raw-null-notequal','customAttributeFilter','SKULocAttr15','notequalto','-')
    one('raw-null-negative-like','customAttributeFilter','SKULocAttr15','doesnotcontain','-')
    one('location-custom','customAttributeFilter','LocAttr2','equalto','Receiving')
    one('pair-custom','customAttributeFilter','SKULocAttr1','equalto','LDC006')
    for op in ('greaterthan','greaterthanequalto','smallerthan','smallerthanequalto'):
        one('norm-'+op,'availabilityFilter','norm',op,'300')
    one('positive-stock','availabilityFilter','stock','greaterthan','0')
    one('git-zero','availabilityFilter','git','equalto','0')
    one('virtual-norm','availabilityFilter','virtualnorm','greaterthanequalto','0')
    one('pipeline-color','availabilityFilter','pic','equalto','Black')
    one('physical-color','availabilityFilter','ohic','equalto','Green')
    one('location-type','supplyChainFilter','forlocation','equalto','Depo')
    one('for-location-code','supplyChainFilter','forlocationlocationcode','equalto','AG515802')
    one('parent-code','supplyChainFilter','forchildrenlocationcode','equalto','LDC001')
    one('parent-type-join','supplyChainFilter','forchildren','equalto','LDC')
    # Each is proved by the actual DLL's invalid query, never silently repaired.
    for name,group,attribute,extra in (
        ('missing-category','availabilityFilter','category',{}),
        ('missing-tags','availabilityFilter','pipo,seasonality',{}),
        ('missing-availability','availabilityFilter','availability',{}),
        ('missing-coverage','coverageFilter','coverage',{}),
        ('missing-color-count','colorFilter','red',dict(type='colorcount')),
        ('missing-color-age','colorFilter','red',dict(type='colorage'))):
        one(name,group,attribute,'greaterthan' if group=='colorFilter' else 'equalto','1',error=True,**extra)
    one('invalid-operator','productFilter','p2','invented','Selected',error=True)
    one('invalid-hierarchy-column','productFilter','p9','equalto','X',error=True)
    return roster
