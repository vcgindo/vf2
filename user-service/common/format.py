def fomat_column_df(dataframe):
    dataframe.columns = dataframe.columns.str.upper()
    dataframe.columns = dataframe.columns.str.replace(' ', '_')
    dataframe.columns = dataframe.columns.str.replace(
        '(', '', regex=True)
    dataframe.columns = dataframe.columns.str.replace(
        ")", '', regex=True)
    dataframe.columns = dataframe.columns.str.replace(
        ".", '', regex=True)
    return dataframe
