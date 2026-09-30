import pandas as pd
def change_columns(chunk, key_col_map):
    """
    This utility function will change the keys of the list of dictionaries that are getting bulk inserted
    during the add master call.
    """
    
    chunk_df = pd.DataFrame(chunk)
    key_col_map = key_col_map[['key','displayName']]
    key_col_map = key_col_map.set_index('key')['displayName'].to_dict()
    chunk_df.rename(columns=key_col_map, inplace=True)
    try:
        chunk_df.drop(columns=['Error_Message'], inplace=True)   ## This needs to be handeled in a serializer
    except:
        pass
    try:
        chunk_df.drop(columns=['error'], inplace=True)   ## This needs to be handeled in a serializer
    except:
        pass
    try:
        chunk_df.drop(columns=['warning'], inplace=True)   ## This needs to be handeled in a serializer
    except:
        pass
    chunk = chunk_df.to_dict(orient='records')
    return chunk