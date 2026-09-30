
def replace_columns(list_of_columns, column_map):
    """This function just simply replaces the column names
    passed in a list with the fronte-end headers"""
    reverse_column_map = {v: k for k, v in column_map.items()}
    for index,column in enumerate(list_of_columns):
        list_of_columns[index] = reverse_column_map[column]
    return list_of_columns