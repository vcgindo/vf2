def replace_headers_with_keys_streaming(df,ui_config, master_id):
    temp = {}
    if int(master_id) < 14:   # condition to handle nms masters
        for column_name,_ in df.items():
            for column_definition in ui_config:
                if column_definition['displayName'] == column_name.strip():
                    temp[column_definition['key']] = column_definition['displayName']
                    df.rename(columns={column_name:column_definition['key']},inplace = True)
    else:                     # condition to handle retail app
        for column_name,_ in df.items():
            for column_definition in ui_config:
                if column_definition['displayName'] == column_name:
                    temp[column_definition['key']] = column_definition['displayName']
                    df.rename(columns={column_name:column_definition['key']},inplace = True)
                    break
    return temp

def replace_headers_with_keys(df,ui_config, master_id):
    ui_config = ui_config[['displayName','key']]
    columns_replacements = ui_config.set_index('displayName')['key'].to_dict()
    df.rename(columns = columns_replacements, inplace = True)
    data = df.to_dict(orient = 'records')
    return data

def replace_keys_with_headers(df = None, ui_config = None, master_id = None, filter_col = None):
    if filter_col is not None:
        ui_config = ui_config[['col_code','header']]
        columns_replacements = ui_config.set_index('col_code')['header'].to_dict()
        if filter_col in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
            return filter_col
        return columns_replacements[filter_col]  
    ui_config = ui_config[['key','displayName']]
    columns_replacements = ui_config.set_index('key')['displayName'].to_dict()  
    df.rename(columns = columns_replacements, inplace = True)
    df.columns = df.columns.str.lower()
    data = df.to_dict(orient = 'records')
    return data