def sanitize_master(master_df):
    for j in master_df.columns:
        master_df[j] = master_df[j].apply(lambda x: x.upper().strip() if (type(x) == str) else x)