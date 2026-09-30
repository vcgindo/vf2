from apps.settings import CUSTOM_DATETIME, MAXIMUM_STOCK_CAPACITY_FOR_IST_PACKETS

def generate_ist_global_track_id(temp_ist_df, is_ist_type_auto=True):
    
    # sorting dataframe
    temp_ist_df.sort_values(by=['donor_wh_code', 'receiver_wh_code', 'sku_code' ,'quantity_to_be_moved'], inplace=True)
    
    # generate combo key with prefix as per the ist type
    if is_ist_type_auto:
        temp_ist_df['wh_combo'] = temp_ist_df['donor_wh_code'].astype(str) + '_' + temp_ist_df['receiver_wh_code'].astype(str)
    else:    
        temp_ist_df['wh_combo'] = temp_ist_df['donor_wh_code'].astype(str) + '_' + temp_ist_df['receiver_wh_code'].astype(str)
    
    cumulative_sum = 0
    prev_combo_key = None
    final_cumulative_sum = []
    id_suffix = 0
    for index, row in temp_ist_df.iterrows():
        if prev_combo_key != row['wh_combo']:
            # Here the donor - receiver combination changed so we need to increment the id_suffix 1
            id_suffix = id_suffix + 1
            cumulative_sum = row['quantity_to_be_moved']
        
        else:
            cumulative_sum += row['quantity_to_be_moved']
        
        if cumulative_sum > MAXIMUM_STOCK_CAPACITY_FOR_IST_PACKETS:
            # package capacity is exceeding so, do the following 
            # 1. reset the cumulative sum to current row quantity 
            # 2. increment the id suffix to have new id for the new package
            cumulative_sum = row['quantity_to_be_moved']
            id_suffix = id_suffix + 1
        
        # else if sum is under capcity so we can use the same package hence keep the id suffix same i.e. no need to change
        # append the id suffix to the final list of id suffixes
        final_cumulative_sum.append(int(id_suffix))
        prev_combo_key = row['wh_combo']
        
    temp_ist_df['cumulative_sum'] = final_cumulative_sum
    
    # generating final ist global track id
    temp_ist_df['ist_global_track_id'] = 'V' + CUSTOM_DATETIME.strftime("%d%m%y%H") +  temp_ist_df['cumulative_sum'].astype(str)

    # drop the temporary columns
    temp_ist_df = temp_ist_df.drop(['wh_combo', 'cumulative_sum'], axis=1)

    return temp_ist_df