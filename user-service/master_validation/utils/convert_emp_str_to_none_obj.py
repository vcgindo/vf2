def convert_empstr_to_none(value):
    if isinstance(value, str) and value.strip() == '':
        return None
    return value