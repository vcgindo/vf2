import os

from ..interceptors import IST_INTERCEPTOR, MTA_INTERCEPTOR, MTO_INTERCEPTOR

service_map = {
    'ist':{
        'base_url':'http://localhost',
        'port':'5200',
        'interceptor':IST_INTERCEPTOR,
        'active':False,
        'application_id':1
    },
    'mta':{
        'base_url':os.environ.get('MTA_BACKEND_URL', 'http://localhost:5153'),
        'port':'',
        'interceptor':MTA_INTERCEPTOR,
        'active':True,
        'application_id':2
    },
    'mto':{
        'base_url':os.environ.get('MTO_BACKEND_URL', 'http://localhost:10015'),
        'port':'',
        'interceptor':MTO_INTERCEPTOR,
        'active':True,
        'application_id':3
    }   
}
