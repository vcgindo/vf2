def convert_str_to_bool(value):
    if type(value) != bool and value.upper() == 'TRUE' :
        return True
    elif type(value) != bool and value.upper() == 'FALSE':
        return False
    return value