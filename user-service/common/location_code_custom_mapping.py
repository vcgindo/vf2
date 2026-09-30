# write a function which will take df as input which will have column name 'wh_code' , read a csv files name wh_code_mapping.csv which will have 2 columns wh_code and new_wh_code , now replace the wh_code column using the mapping in the csv and return the dataframe
import pandas as pd
import os
from common.file import File
from common.logger import get_logger
logger = get_logger(__name__)


def apply_wh_code_custom_mapping(input_df : pd.DataFrame):
    file_path = File("master/LocationMappingMaster.csv").get_full_path()

    # Check if the file exists
    if not os.path.isfile(file_path):
        logger.debug("Location Mapping File does not exist. Using the location codes as it is..")
        return input_df

    try:
        # read the csv file
        mapping_df = pd.read_csv(
                    file_path,
                    low_memory=False,
                    dtype={"old_wh_code": "str" , "new_wh_code": "str"}
                )
    except Exception as e:
        logger.error(f"Error while reading LocationMappingMaster : {e}")

    if mapping_df.empty:
        logger.debug("Location Mapping File is empty. Using the location codes as it is..")
        return input_df

    # Check if mapping_df is not empty and 'old_wh_code' and 'new_wh_code' columns exist
    if 'old_wh_code' not in mapping_df.columns or 'new_wh_code' not in mapping_df.columns:
        raise Exception("Location Mapping file is NOT empty BUT does not contain necessary columns. Exiting..")

    # merge the dataframe with the csv file
    
    # rename column old_wh_code in input df to wh_code
    mapping_df.rename(columns={"old_wh_code": "wh_code"}, inplace=True)
    try:
        merged_df = input_df.merge(mapping_df, on = 'wh_code', how = 'left')
        
        # Replace the 'wh_code' column with the mapped values
        merged_df['new_wh_code'].fillna(merged_df['wh_code'], inplace=True)
        merged_df['wh_code'] = merged_df['new_wh_code']
        
        # Drop the 'new_wh_code' column as it's no longer needed
        merged_df.drop(columns=['new_wh_code'], inplace=True)
        
        return merged_df
    
    except Exception as e:
        logger.error(f"Error while applying location mapping : {e}")