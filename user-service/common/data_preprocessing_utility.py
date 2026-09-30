import pandas as pd


def clean_dataframe(df):
    """
    Cleans the given dataframe by removing leading/trailing whitespaces and commas from string columns.

    Args:
        df (pandas.DataFrame): The dataframe to be cleaned.

    Returns:
        pandas.DataFrame: The cleaned dataframe.
    """
    # df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    # df = df.applymap(lambda x: x.replace(',', '') if isinstance(x, str) else x)
    df = df.apply(lambda col: col.str.strip() if col.dtype == 'object' else col)
    df = df.apply(lambda col: col.str.replace(',', '') if col.dtype == 'object' else col)
    return df