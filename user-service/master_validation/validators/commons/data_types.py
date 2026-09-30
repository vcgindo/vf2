COMMON_DTYPE = {
    'c1':str,
    'c2':str,
    'c3':str,
    'c4':str,
    'c5':str,
    'c6':str,
    'c7':str,
    'c8':str,
    'c9':str,
    'c10':str,
    'c11':str,
    'c12':str,
    'c13':str,
    'c14':str,
    'c15':str,
}

SKU_DTYPE = {
    'sc':str,
    'sd':str,
    'ec':int,
    'wt':float,
    'vm':float,
    **COMMON_DTYPE
}

LOCATION_DTYPE = {
   'wc':str,
   'wd':str,
   'l':str,
   **COMMON_DTYPE 
}

SKU_LOCATION_DTYPE = {   
    'sc': str,
    'wc':str,
    'wd':str,
    'pwc':str,
    'pd':str,
    'n':int,
    'mn':int,
    'rlt':int,
    'rcp':int,
    'gcp':int,
    'ocp':int,
    'moc':int,
    'ps':int,
    'st':float,
    'dst':float,
    'pt':float,
    'dpt':float,
    'npr':float,
    'frf':str,
    'da':str,
    **COMMON_DTYPE
}

SOB_DTYPE = {
    'sc': str,
    'wc':str,
    'SuppCode':str,
    'SOB':float
}

MOQ_DTYPE = {
    'sc': str,
    'wc':str,
    'SuppCode':str,
    'MOQ':int
}

STOP_PIPO_DTYPE = {
    'sc':str,
    'posn':str,
    'wc':str,
    'ln':str,
    'onm':int,
    'cn':int,
    'nc':str,
    'pd':str,
    'pis':str,
    'pisn':str,
    'pcn':int,
    'ptn':int

}

ADD_PO_DTYPE = {
    'sc':str,
    'wc':str
}

ADD_PIPO_DTYPE = {
    'sc':str,
    'wc':str,
    'pi':str
}

ADD_TARGET_NORM_DTYPE = {
    'sc':str,
    'wc':str,
    'tn':int
}

SEASONALITY_STATUS_DTYPE = {
    'sc':str,
    'wc':str,
    'wd':str,
    'sd':str,
    'ed':str,
    'tn':int,
    'rlt':int,
    'dnp':int,
    'nn':int,
    'onm':int,
    'ulc':int,
    'bd':int,
    'tp':str,
    'sts':str,
    'cmt':str,
    'skd':str
}

ABSOLUTE_VALUE_SEASONALITY_DTYPE = {
    'sc':str,
    'wc':str,
    'sd':str,
    'ed':str,
    'tn':int,
    'bd':float
}

DELTA_PERCENTAGE_SEASONALITY_DTYPE = {
    'sc':str,
    'wc':str,
    'sd':str,
    'ed':str,
    'dnp':int,
    'ulc':int,
    'bd':float
}

FORCE_NORM_CHANGE_DTYPE = {
    'sc':str,
    'wc':str,
    'nn':int
}
