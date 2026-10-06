"""Pure direct port of the four deployed nonempty GIT chart datasets.

Authority: pinned deployed ExpediteProcessor SHA256
``e78148cc38d5a802e014e6085111e79a40c2a6b462563e2bd412677505e654b4``
(``GetChildGoodsInTransitGraphDetails`` and ``GetGoodsInTransitResponse``).

All source occurrences, join multiplication and NULL behavior are retained.
Callers must supply the separate SiteDescriptionTbl population and an explicit
LocAttr dynamic-column/config binding; neither is inferred from shipment facts.
Fixtures used by tests are connector cases, not retained shipment metadata.
"""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from mta.presentation.rrr import sql_key


SOURCE_SHA256 = 'e78148cc38d5a802e014e6085111e79a40c2a6b462563e2bd412677505e654b4'
BASE_CONFIG = [dict(header='LL'+str(i),colCode='ll'+str(i),colPosition=0)
               for i in range(1,6)]


def _index(rows, *fields):
    result=defaultdict(list)
    for row in rows:
        key=sql_key(*(row.get(field) for field in fields))
        if key is not None:result[key].append(row)
    return result


def _scope(scope, label):
    values=getattr(scope,'multiplicities',scope)
    if not isinstance(values,dict):raise ValueError(label+' scope requires resolved multiplicities')
    result={}
    for code,weight in values.items():
        if type(weight) is not int or weight<0:raise ValueError(label+' scope weight must be nonnegative integer')
        key=sql_key(code)
        if key is not None and weight:result[key]=result.get(key,0)+weight
    return result


def _dynamic(dynamic_attributes, dynamic_ui_config):
    if not isinstance(dynamic_attributes,(list,tuple)) or any(
            not isinstance(item,(list,tuple)) or len(item)!=2 or
            not all(isinstance(value,str) and value for value in item)
            for item in dynamic_attributes):
        raise ValueError('Explicit LocAttr dynamic attribute bindings required')
    aliases=[alias for alias,_ in dynamic_attributes]
    if len(set(aliases))!=len(aliases):raise ValueError('Duplicate dynamic location alias')
    if not isinstance(dynamic_ui_config,list) or any(not isinstance(row,dict) for row in dynamic_ui_config):
        raise ValueError('Explicit LocAttr dynamic UI configuration required')
    configured=[row.get('colCode') for row in dynamic_ui_config]
    if configured!=aliases:raise ValueError('Dynamic location attributes/configuration differ')
    return list(dynamic_attributes),[dict(row) for row in dynamic_ui_config]+[dict(row) for row in BASE_CONFIG]


def _key_value(value):
    return sql_key(value) if isinstance(value,str) else ('value',value)


def _dimension_rows(code, descriptions, attributes):
    key=sql_key(code)
    if key is None:return ()
    return ((description,attribute) for description in descriptions.get(key,())
            for attribute in attributes.get(key,()))


def _location_values(code, description, attribute, dynamic):
    values=dict(WhCode=code,Details=str(description['WHDescription']).replace("'",''),
                LogisticsLocation=attribute.get('LogisticsLocation'))
    for alias,column in dynamic:values[alias]=attribute.get(column)
    for i in range(1,6):values['ll'+str(i)]=attribute.get('LL'+str(i))
    return values


def _group_key(values, names):
    return tuple(_key_value(values.get(name)) for name in names)


def _expanded_value(values, position):
    remaining=position
    for value,weight in values:
        if remaining<weight:return value
        remaining-=weight
    raise IndexError(position)


def _percentile(values, fraction):
    ordered=sorted((Decimal(value),weight) for value,weight in values if weight)
    total=sum(weight for _,weight in ordered)
    if not total:return None
    position=Decimal(total-1)*fraction
    lower=int(position);upper=lower if position==lower else lower+1
    low=_expanded_value(ordered,lower);high=_expanded_value(ordered,upper)
    value=low+(high-low)*(position-Decimal(lower))
    return value.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)


def _mean(values):
    total=sum(weight for _,weight in values)
    if not total:return None
    value=sum(Decimal(item)*weight for item,weight in values)/Decimal(total)
    return value.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)


def _delay_cte(transporter, transit, products, locations, partition):
    raw=_index(transit,'SKUCode','WhCode');rows=[];partitions=defaultdict(list)
    for truck in transporter:
        product_weight=products.get(sql_key(truck.get('SKUCode')),0)
        location_weight=locations.get(sql_key(truck.get('WhCode')),0)
        if not product_weight or not location_weight or truck.get('IsReceiving') not in (True,1):continue
        for shipment in raw.get(sql_key(truck.get('SKUCode'),truck.get('WhCode')),()):
            tlt,slt=shipment.get('TLT'),shipment.get('SLT')
            if tlt is None or slt is None or tlt<=slt:continue
            weight=product_weight*location_weight
            row=dict(SKUCode=truck.get('SKUCode'),WhCode=truck.get('WhCode'),
                     ParentWhCode=truck.get('ParentWhCode'),TransporterCode=truck.get('TransporterCode'),
                     OrderNo=truck.get('OrderNo'),DelayDays=tlt-slt,weight=weight)
            rows.append(row);partitions[sql_key(row[partition])].append((row['DelayDays'],weight))
    stats={key:dict(Median=_percentile(values,Decimal('0.5')),
                    Q1=_percentile(values,Decimal('0.25')),
                    Q3=_percentile(values,Decimal('0.75')))
           for key,values in partitions.items()}
    return rows,stats


def _delay_dataset(transporter, transit, descriptions, attributes, products, locations,
                   dynamic, *, partition):
    cte,stats=_delay_cte(transporter,transit,products,locations,partition)
    matched=defaultdict(list)
    for row in cte:
        matched[sql_key(row['SKUCode'],row['WhCode'],row['ParentWhCode'],
                        row['TransporterCode'],row['OrderNo'])].append(row)
    groups={}
    for truck in transporter:
        matches=matched.get(sql_key(truck.get('SKUCode'),truck.get('WhCode'),truck.get('ParentWhCode'),
                                    truck.get('TransporterCode'),truck.get('OrderNo')),())
        if not matches:continue
        for description,attribute in _dimension_rows(truck.get('WhCode'),descriptions,attributes):
            location=_location_values(truck.get('WhCode'),description,attribute,dynamic)
            if partition=='WhCode':
                names=('WhCode','Details','LogisticsLocation',*[alias for alias,_ in dynamic],
                       'll1','ll2','ll3','ll4','ll5')
                values=location
            else:
                names=('TransporterCode','TransporterName')
                values=dict(TransporterCode=truck.get('TransporterCode'),
                            TransporterName=truck.get('TransporterName'))
            key=_group_key(values,names)
            group=groups.setdefault(key,dict(values=values,count=0,delays=[]))
            for match in matches:
                if truck.get('LRCode') is not None:group['count']+=match['weight']
                group['delays'].append((match['DelayDays'],match['weight']))
    output=[]
    for group in groups.values():
        delays=group['delays'];values=dict(group['values'])
        partition_key=sql_key(values[partition])
        values.update(LRCount=group['count'],MinDelayDays=min(value for value,_ in delays),
                      MaxDelayDays=max(value for value,_ in delays),Mean=_mean(delays),
                      **stats[partition_key])
        output.append(values)
    return output


def datasets(*, transporter, transit, git_master, location_attributes,
             location_descriptions, product_scope, location_scope,
             dynamic_attributes, dynamic_ui_config):
    """Return the four canonical DataSet tables plus the exact UI configuration."""
    dynamic,config=_dynamic(dynamic_attributes,dynamic_ui_config)
    products=_scope(product_scope,'product');locations=_scope(location_scope,'location')
    descriptions=_index(location_descriptions,'WHCode');attributes=_index(location_attributes,'WHCode')

    eligible=defaultdict(int)
    for row in git_master:
        color=sql_key(row.get('PhysicalInventoryColor'))
        product_weight=products.get(sql_key(row.get('SKUCode')),0)
        location_weight=locations.get(sql_key(row.get('ParentWhCode')),0)
        if (color in {('red',),('black',)} and row.get('Git') is not None and row['Git']>0
                and row.get('IsParent') in (True,1) and product_weight and location_weight):
            eligible[sql_key(row.get('SKUCode'),row.get('WhCode'))]+=product_weight*location_weight
    location_groups={}
    for truck in transporter:
        weight=eligible.get(sql_key(truck.get('SKUCode'),truck.get('WhCode')),0)
        if not weight:continue
        for description,attribute in _dimension_rows(truck.get('WhCode'),descriptions,attributes):
            values=_location_values(truck.get('WhCode'),description,attribute,dynamic)
            values['SKUStatus']=truck.get('SKUStatus')
            names=('WhCode','Details','LogisticsLocation',*[alias for alias,_ in dynamic],
                   'll1','ll2','ll3','ll4','ll5','SKUStatus')
            key=_group_key(values,names)
            group=location_groups.setdefault(key,dict(values=values,counts=0))
            if truck.get('SKUCode') is not None:group['counts']+=weight
    location_status=[]
    for group in location_groups.values():location_status.append(dict(counts=group['counts'],**group['values']))
    location_status.sort(key=lambda row:(sql_key(row['WhCode']),-row['counts']))

    transporter_groups={}
    for truck in transporter:
        weight=products.get(sql_key(truck.get('SKUCode')),0)*locations.get(sql_key(truck.get('WhCode')),0)
        if not weight or sql_key(truck.get('PhysicalInventoryColor')) not in {('red',),('black',)}:continue
        values=dict(TransporterCode=truck.get('TransporterCode'),TruckStatus=truck.get('TruckStatus'),
                    TransporterName=truck.get('TransporterName'))
        key=_group_key(values,('TransporterCode','TruckStatus','TransporterName'))
        group=transporter_groups.setdefault(key,dict(values=values,counts=0))
        if truck.get('LRCode') is not None:group['counts']+=weight
    transporter_status=[dict(counts=group['counts'],**group['values']) for group in transporter_groups.values()]
    transporter_status.sort(key=lambda row:-row['counts'])

    location_delay=_delay_dataset(transporter,transit,descriptions,attributes,products,locations,
                                  dynamic,partition='WhCode')
    transporter_delay=_delay_dataset(transporter,transit,descriptions,attributes,products,locations,
                                     dynamic,partition='TransporterCode')
    return dict(tables=[location_status,location_delay,transporter_status,transporter_delay],
                ui_config=config)


def _wire(value):
    if value is None:return ''
    if isinstance(value,bool):return 'True' if value else 'False'
    return str(value)


def response(dataset):
    """Port GetGoodsInTransitResponse's four-table string-valued wire assembly."""
    if not isinstance(dataset,dict) or len(dataset.get('tables',()))!=4:
        raise ValueError('Four canonical GIT chart datasets required')
    location_status,location_delay,transporter_status,transporter_delay=dataset['tables']
    config=dataset.get('ui_config')
    if not isinstance(config,list):raise ValueError('GIT chart UI configuration required')
    codes=[row.get('colCode') for row in config]

    def status_rows(rows,group,status,name_field):
        ordered=[];seen=set()
        for row in rows:
            key=sql_key(row.get(group))
            if key not in seen:seen.add(key);ordered.append((key,row))
        output=[]
        for key,first in ordered:
            members=[row for row in rows if sql_key(row.get(group))==key]
            delay=superdelay='0'
            for row in members:
                if row.get(status)=='SuperDelay':superdelay=_wire(row.get('counts'))
                elif row.get(status)=='Delay':delay=_wire(row.get('counts'))
            item=dict(superdelay=superdelay,delay=delay,name=_wire(first.get(name_field)))
            for code in codes:
                if code in first:item[code]=_wire(first.get(code))
            output.append(item)
        return output

    def delay_rows(rows,transporterwise=False):
        output=[]
        for row in rows:
            item=dict(name=_wire(row.get('TransporterName' if transporterwise else 'Details')),
                      mean=_wire(row.get('Mean')),mind=_wire(row.get('MinDelayDays')),
                      median=_wire(row.get('Median')),maxd=_wire(row.get('MaxDelayDays')),
                      Q1=_wire(row.get('Q1')),Q3=_wire(row.get('Q3')))
            item['TransporterCode' if transporterwise else 'LogisticsLocation']=_wire(
                row.get('TransporterCode' if transporterwise else 'LogisticsLocation'))
            for code in codes:
                if code in row:item[code]=_wire(row.get(code))
            output.append(item)
        return output

    location=dict(
        maxTechBlackRedColumn=dict(data=status_rows(location_status,'WhCode','SKUStatus','Details'),uiconfig=config),
        delayDaysStatisticalBox=dict(data=delay_rows(location_delay),uiconfig=config))
    transporterwise=dict(
        maxTechBlackRedColumn=dict(data=status_rows(transporter_status,'TransporterCode','TruckStatus','TransporterName'),uiconfig=config),
        delayDaysStatisticalBox=dict(data=delay_rows(transporter_delay,True),uiconfig=config))
    return dict(data=dict(transporterWise=transporterwise,locationWise=location))


def build(**inputs):
    return response(datasets(**inputs))
