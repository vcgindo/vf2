"""Versioned typed daily input images, including nested policy/task collections.

Only shape/receipt/config metadata lives in the manifest. All nonempty sequences
are typed images. Projection sequences borrow their source without building a
second population; insert batching belongs to relational_state.bulk.
"""
from collections.abc import Sequence
from mta.row_sequences import RecordRows
from mta.serialization import digest, storage
from mta.runtime.relational_state import STORAGE_TABLES, save_image, load_image

SCHEMA='fresh-daily-input-manifest-v2'


class Rows(Sequence):
    def __init__(self, length, factory):self.length,self.factory=length,factory
    def __len__(self):return self.length
    def __iter__(self):return iter(self.factory())
    def __getitem__(self,index):
        if not isinstance(index,int) or index<0:raise IndexError(index)
        for ordinal,row in enumerate(self):
            if ordinal==index:return row
        raise IndexError(index)


def shape(value, path=()):
    if isinstance(value,dict):
        return ['dict',[[k,shape(v,(*path,k))] for k,v in value.items()]]
    if isinstance(value,(list,tuple,RecordRows)):return ['list',list(path)]
    return ['value',list(path)]


def leaves(node, kind):
    if node[0]=='dict':
        for _,child in node[1]:yield from leaves(child,kind)
    elif node[0]==kind:yield tuple(node[1])


def get(value,path,default=None):
    for key in path:
        if not isinstance(value,dict) or key not in value:return default
        value=value[key]
    return value


def choose_table(fields,path,rows=None):
    from mta.runtime.complete_daily_state import input_table
    from mta.runtime.input_tables import TEXT_VEHICLE_TABLES
    names={f.casefold() for f in fields}
    if path in ('input/profile/daily/module_sources/distributor_norms/values',
                'input/profile/daily/module_sources/vendor_master/values'):
        if names and names != {'skucode','whcode'}:
            raise ValueError('Daily module master projection fields differ')
        return 'Intermediate/SKULoc_DailyData'
    from mta.runtime.dbm_phase_storage import TABLE as PHASE_TABLE, OPENING as PHASE_OPENING
    from mta.runtime.btr_history_storage import TABLE as BTR_TABLE, OPENING as BTR_OPENING, FROZEN as BTR_FROZEN
    if path in (BTR_OPENING,BTR_FROZEN):
        if names and names != {name.casefold() for name,_ in STORAGE_TABLES[BTR_TABLE]}:
            raise ValueError('BTR history typed input field roster differs')
        return BTR_TABLE
    if path == 'input/profile/delivery/btr_history/importer_vf_settings/values':
        if names and names != {'parameter','value','description'}:
            raise ValueError('BTR Importer settings typed field roster differs')
        return 'Importer/VFSettings'
    if path == PHASE_OPENING:
        if names and names != {name.casefold() for name, _ in STORAGE_TABLES[PHASE_TABLE]}:
            raise ValueError('Phase recommendation typed input field roster differs')
        return PHASE_TABLE
    text_path = {
        'input/profile/calculation/logistics/vehicles/values': 'input/vehicle_text',
        'input/profile/calculation/logistics/location_vehicles/values': 'input/location_vehicle_text',
    }.get(path)
    if text_path and rows:
        identities = [row.get('vehicle_id') for row in rows
                      if row.get('vehicle_id') is not None]
        if identities and all(isinstance(value,str) for value in identities):
            if not names <= {name.casefold() for name,_ in STORAGE_TABLES[text_path]}:
                raise ValueError('Text vehicle input fields differ: '+path)
            return text_path
    phase_paths = {'input/mdm_input/phase_controls/phase_requests/values': 'input/phase_out_queue',
        'input/mdm_input/phase_controls/phase_in_requests/values': 'input/phase_in_norm_queue',
        'input/mdm_input/phase_controls/task_revisions/values': 'input/phase_controls_task_revision'}
    if path in phase_paths:
        table = phase_paths[path]
        if names != {n.casefold() for n, _ in STORAGE_TABLES[table]}:
            raise ValueError('Phase controls typed capture field roster differs')
        return table
    stop_paths = {'input/mdm_input/stop_pipo/rows/values': 'input/stop_pipo_queue',
        'input/mdm_input/stop_pipo/task_revisions/values': 'input/stop_pipo_task_revision'}
    if path in stop_paths:
        table = stop_paths[path]
        if names != {n.casefold() for n, _ in STORAGE_TABLES[table]}:
            raise ValueError('StopPIPO typed capture field roster differs')
        return table
    season_paths = {'input/mdm_input/season/rows/values': 'input/season_queue',
        'input/mdm_input/season/current/values': 'input/season_current',
        'input/mdm_input/season/task_revisions/values': 'input/season_task_revision'}
    if path in season_paths:
        table = season_paths[path]
        if names != {n.casefold() for n, _ in STORAGE_TABLES[table]}:
            raise ValueError('Seasonality typed capture field roster differs')
        return table
    force_paths = {'input/mdm_input/force/rows/values': 'input/force_queue',
        'input/mdm_input/force/upload_log/values': 'input/force_upload_log',
        'input/mdm_input/force/task_revisions/values': 'input/force_task_revision'}
    if path in force_paths:
        table = force_paths[path]
        if names != {name.casefold() for name, _ in STORAGE_TABLES[table]}:
            raise ValueError('Force capture typed field roster differs')
        return table
    if path == 'input/mdm_input/supplier/task_revisions/values':
        if names != {'master_id', 'task_id', 'revision'}:
            raise ValueError('Supplier task revision fields differ')
        return 'input/supplier_task_revision'
    supplier_queue = {'NMSSOB': 'sob', 'NMSMOQWithDestination': 'moq_with_destination',
                      'NMSMOQWithoutDestination': 'moq_without_destination'}
    for queue, suffix in supplier_queue.items():
        if path == 'input/mdm_input/supplier/queues/' + queue + '/values':
            table = 'input/supplier_' + suffix
            if not names <= {name.casefold() for name, _ in STORAGE_TABLES[table]}:
                raise ValueError('Supplier capture fields differ')
            return table
    complete = input_table(path)
    if complete:
        if not names <= {name.casefold() for name,_ in STORAGE_TABLES[complete]}:
            raise ValueError('Complete-day input fields differ from declared population: '+path)
        return complete
    candidates=[key for key,columns in STORAGE_TABLES.items() if key not in (PHASE_TABLE,BTR_TABLE)
                if not key.startswith(('complete/', 'input/supplier_', 'input/force_', 'input/season_', 'input/stop_pipo_', 'input/phase_', 'input/production_', 'production/'))
                and key not in TEXT_VEHICLE_TABLES
                and names<={name.casefold() for name,_ in columns}]
    if not candidates:raise ValueError('Unmapped typed input family: '+path+' '+str(sorted(fields)))
    # Explicit input families take precedence; closing schema is reusable only
    # for exact native field names. Every chosen mapping is retained and checked.
    return min(candidates,key=lambda key:(not key.startswith('input/'),len(STORAGE_TABLES[key]),key))


def save_input(run,raw, *, image_writer=None, table_selector=None):
    writer = image_writer or save_image
    selector = table_selector or choose_table
    images={}
    def image(path,rows,table=None):
        table=table or selector(rows[0] if rows else (),path,rows)
        from mta.runtime.dbm_phase_storage import TABLE as PHASE_TABLE, OPENING as PHASE_OPENING, FROZEN as PHASE_FROZEN
        if image_writer is None and table == PHASE_TABLE and path == PHASE_OPENING:
            # Frozen predecessor rows are owned by the run, not by the native
            # initialization namespace. Their manifest preserves source shape.
            path = PHASE_FROZEN
        from mta.runtime.btr_history_storage import TABLE as BTR_TABLE, OPENING as BTR_OPENING, FROZEN as BTR_FROZEN
        if image_writer is None and table == BTR_TABLE and path == BTR_OPENING:
            path = BTR_FROZEN
        images[path]=writer(run,path,None,rows,table=table)
        return path

    def pack(value,path):
        if isinstance(value,dict):
            return {'object':[[k,pack(v,path+'/'+k)] for k,v in value.items()]}
        if not isinstance(value,(list,tuple,Rows,RecordRows)):
            return {'scalar':storage(value)}
        if not value:
            if table_selector:
                table = selector((), path+'/values', [])
                if table is None:
                    return {'empty': True}
                return {'records': image(path+'/values', [], table),
                    'shape_image': image(path+'/shape', [], 'input/row_shape'),
                    'shapes': [], 'children': []}
            from mta.runtime.complete_daily_state import input_table
            table = input_table(path + '/values')
            if table:
                return {'records': image(path+'/values', [], table),
                    'shape_image': image(path+'/shape', [], 'input/row_shape'),
                    'shapes': [], 'children': []}
            return {'empty':True}
        if all(not isinstance(v,(dict,list,tuple)) for v in value):
            rows=Rows(len(value),lambda:({'value':v} for v in value))
            kinds={type(v) for v in value if v is not None}
            if kinds<={int}:table='input/integer_values'
            elif kinds<={str}:table='input/string_values'
            else:raise ValueError('Unsupported scalar input collection: '+path)
            return {'scalars':image(path,rows,table)}
        if not all(isinstance(row,dict) for row in value):
            raise ValueError('Input collection requires one declared record family: '+path)
        shapes=[];fields=[];children=[]
        for row in value:
            item=shape(row)
            if item not in shapes:
                shapes.append(item)
                if len(shapes)>128:raise ValueError('Input record schema exceeds bounded shape contract')
                for leaf in leaves(item,'value'):
                    if leaf not in fields:fields.append(leaf)
                for child in leaves(item,'list'):
                    if child not in children:children.append(child)
        projected=Rows(len(value),lambda:({'/'.join(f):get(row,f) for f in fields} for row in value))
        scalar_image=image(path+'/values',projected) if fields else None
        variants=Rows(len(value),lambda:({'shape_id':shapes.index(shape(row))} for row in value))
        result={'records':scalar_image,'shape_image':image(path+'/shape',variants,'input/row_shape'),
                'shapes':shapes,'children':[]}
        for field in children:
            length=sum(len(get(row,field,[])) for row in value)
            childrows=Rows(length,lambda field=field:
                (child for row in value for child in get(row,field,[])))
            links=Rows(length,lambda field=field:
                ({'parent_ordinal':i,'child_ordinal':j} for i,row in enumerate(value)
                 for j,_ in enumerate(get(row,field,[]))))
            childpath=path+'/children/'+'/'.join(field)
            result['children'].append([list(field),pack(childrows,childpath),
                image(childpath+'/links',links,'input/child_link')])
        return result

    tree=pack(raw,'input')
    manifest=dict(schema=SCHEMA,tree=tree,images=images,content_digest=run.input_digest,
                  profile={'delivery':{'site_code':raw['profile']['delivery']['site_code']}})
    from mta.serialization import canonical_parts
    if sum(len(p) for p in canonical_parts(manifest))>1024*1024:
        raise ValueError('Typed input metadata exceeds bounded manifest size')
    return manifest


def read_input(run, *, components=None, image_reader=None):
    reader = image_reader or load_image
    value=run.input_payload
    if (value.get('schema')!=SCHEMA or value['content_digest']!=run.input_digest
            or digest(value)!=run.input_manifest_digest):
        raise ValueError('Typed daily input manifest identity drift')
    def read(path):return reader(run,value['images'][path])
    def unpack(node):
        if 'scalar' in node:return node['scalar']
        if 'empty' in node:return []
        if 'object' in node:return {k:unpack(v) for k,v in node['object']}
        if 'scalars' in node:return [row['value'] for row in read(node['scalars'])]
        types=read(node['shape_image'])
        scalars=read(node['records']) if node['records'] else [{} for _ in types]
        if len(types)!=len(scalars):raise ValueError('Typed input shape population drift')
        def rebuild(template,row):
            if template[0]=='dict':return {k:rebuild(v,row) for k,v in template[1]}
            if template[0]=='list':return []
            return row['/'.join(template[1])]
        def records():
            for item,row in zip(types,scalars):
                shape_id = item['shape_id']
                if type(shape_id) is not int or not 0 <= shape_id < len(node['shapes']):
                    raise ValueError('Typed input shape identity drift')
                yield rebuild(node['shapes'][shape_id],row)
        # Nested child owners require mutable parents; flat histories do not.
        rows = (RecordRows(len(types), records) if not node['children'] and len(types)>10000
                else list(records()))
        for field,child,link in node['children']:
            values=unpack(child);links=read(link)
            if len(values)!=len(links):raise ValueError('Typed input child population drift')
            for item,childvalue in zip(links,values):
                target=get(rows[item['parent_ordinal']],field)
                if not isinstance(target,list) or len(target)!=item['child_ordinal']:
                    raise ValueError('Typed input child ownership/order drift')
                target.append(childvalue)
        return rows
    tree=value['tree']
    if components is not None:
        tree={'object':[[k,v] for k,v in tree['object'] if k in components]}
    return unpack(tree)
