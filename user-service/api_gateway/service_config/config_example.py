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
        'base_url':'http://localhost',
        'port':'5149',
        'interceptor':MTA_INTERCEPTOR,
        'active':False,
        'application_id':2
    },
    'mto':{
        'base_url':'http://127.0.0.1',
        'port':'8000',
        'interceptor':MTO_INTERCEPTOR,
        'active':True,
        'application_id':3
    }   
}
