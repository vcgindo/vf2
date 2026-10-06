"""Shared connector inputs for independent SQL and PostgreSQL GIT count proof."""
from copy import deepcopy


def fixture():
    def truck(sku='A', wh='L', parent='P', order='O', transporter='T', color='Red'):
        return dict(SKUCode=sku, WhCode=wh, ParentWhCode=parent, OrderNo=order,
                    TransporterCode=transporter, PhysicalInventoryColor=color)
    return dict(
        Transporter=[truck(), truck(), truck(sku='B'), truck(order='O2'),
                     truck(order=None), truck(parent='Q'), truck(wh='X'),
                     truck(wh='NO-DESC'), truck(order='GREEN', color='Green'),
                     truck(sku=None), truck(order='o ', transporter='t ')],
        Standard=[dict(SKUCode='A', WhCode='L',Tags='tag'), dict(SKUCode='A', WhCode='L',Tags='tag')],
        Rationed=[dict(SKUCode=s, WhCode=w,Norm=1 if s=='B' else 5) for s,w in
                  [('A','L'), ('A','L'), ('B','L'), ('A','X'), ('A','NO-DESC')]],
        LocDesc=[dict(WHCode=w) for w in ['L','L','X']],
        Loc=[dict(WHCode=w,LL1='North' if w=='L' else 'South',LocationType='Depo',c1='C')
             for w in ['L','L','X','NO-DESC']],
        Pair=[dict(SKUCode='A', LocCode='L'), dict(SKUCode='A', LocCode='L')])


def cases():
    return deepcopy([
        dict(id='all', products=['A','B'], locations=['P','Q'], expected=5),
        dict(id='parent-scope', products=['A','B'], locations=['P'], expected=4),
        dict(id='other-parent', products=['A'], locations=['Q'], expected=1),
        dict(id='product-only-b', products=['B'], locations=['P'], expected=1),
        dict(id='destination-is-not-scope', products=['A'], locations=['L'], expected=0),
        dict(id='empty-products', products=[], locations=['P'], expected=0),
        dict(id='empty-locations', products=['A'], locations=[], expected=0),
        dict(id='sku-filter', products=['A','B'], locations=['P','Q'],expected=1,
             filters=dict(productFilter=dict(filters=[dict(attributeName='sku',operator='equalto',value='B')]))),
        dict(id='location-hierarchy', products=['A','B'], locations=['P','Q'],expected=4,
             filters=dict(locationFilter=dict(filters=[dict(attributeName='l1',operator='equalto',value='North')]))),
        dict(id='colour', products=['A','B'], locations=['P','Q'],expected=0,
             filters=dict(availabilityFilter=dict(filters=[dict(attributeName='ohic',operator='equalto',value='Black')]))),
        dict(id='norm-report-owner', products=['A','B'], locations=['P','Q'],expected=1,
             filters=dict(availabilityFilter=dict(filters=[dict(attributeName='norm',operator='smallerthan',value='2')]))),
        dict(id='tags-standard-owner', products=['A','B'], locations=['P','Q'],expected=4,
             filters=dict(availabilityFilter=dict(filters=[dict(attributeName='pipo,seasonality',operator='equalto',value='tag')]))),
    ])
