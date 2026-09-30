from ..utils.master_sanitization import sanitize_master
from ..utils.replace_colnames_in_list import replace_columns
import pandas as pd
import json
import copy
from ..models.excel_upload import *
class RetailMaster:
    """
    This class defines all the retail master specific validation related operations:
    1) is_valid_integer : checks if data is integer
    2) sanitize_master : functionality to remove extra spaces from string data
    3) validation : ensure that all the validation rules are followed by the master data
    """
    def __init__(self, master_df, validation_rules):
        self.master_df = master_df
        self.validation_rules = validation_rules
        self.master_df['error'] = ''
        self.master_df['warning'] = ''
    def is_valid_integer(self,value):
        """
        Checks if the valueis an integer
        """
        try:
            numeric_value = float(value)
            if numeric_value.is_integer():
                return True
        except (ValueError, TypeError):
            pass
        return False
    def sanitize_master(self, master_df):
        """
        removes extra spaces from the string data
        """
        for j in master_df.columns:
            master_df[j] = master_df[j].apply(lambda x: x.upper().strip() if (type(x) == str) else x)
        return master_df
    
    def validation(self,master_data_df,key_to_header_map,validation_rules,process_id):
        """
        inputs :
        1) master data
        2) map of master column to their keys 
        3) master specific validation rules
        
        Process :
        This function validates each column of the master data using vectorized operations
        and generates 3 additional columns eror, warning and error_message in the same dataframe.
        
        Output:
        This validated master is sent as output
        """
        invalid_data = master_data_df.copy()
        
        unique_columns = [i for i in validation_rules.keys() if validation_rules[i]['IsUnique'] == 'yes']
        df_columns = [key_to_header_map[i] for i in list(invalid_data.columns) if i not in ['error', 'warning', 'error_message','Error']]
        any_missing_unique_col_in_master = set(unique_columns) - set(df_columns)
        invalid_data['error_message'] = ""
        invalid_data['error'] = ""
        invalid_data['warning'] = ""
        unique_columns_shortforms = replace_columns(copy.copy(unique_columns), key_to_header_map)  # in order to execute the duplicated function, we need to replace the column names
        if len(unique_columns) > 0 and not any_missing_unique_col_in_master:
            any_duplicated_entries = invalid_data.duplicated(unique_columns_shortforms, keep = 'first')
            is_duplicated = invalid_data[any_duplicated_entries]
            
            if len(is_duplicated.index) > 0:
                invalid_data.loc[any_duplicated_entries, 'error_message'] += f"Duplicated \'{', '.join(unique_columns)}\', should be unique. "
                invalid_data.loc[any_duplicated_entries, 'error'] += f"Duplicated \'{', '.join(unique_columns)}\', should be unique. "
                
        process = ExcelUpload.objects.get(process_id=process_id)
        process.total_rows = len(master_data_df.columns)
        process.save()
        for index,column in enumerate(master_data_df.columns):
            if (column not in key_to_header_map) or (key_to_header_map[column] not in validation_rules):
                continue

            rules = validation_rules[key_to_header_map[column]]
            is_mandatory = rules['IsMandatory'] == 'yes'

            if is_mandatory:
                is_numeric = rules['IsNumeric'] == 'yes'
                is_date = rules['IsDate'] == 'yes'
                is_decimal = rules['IsDecimal'] == 'yes'
                is_boolean = rules['IsBoolean'] == 'yes'
                
                if is_mandatory:
                    invalid_data.loc[master_data_df[column].isnull(), 'error_message'] += f"'{key_to_header_map[column]}' is mandatory. "
                    invalid_data.loc[master_data_df[column].isnull(), 'error'] += f"'{key_to_header_map[column]}' is mandatory. "
                if is_numeric:
                    invalid_data.loc[~master_data_df[column].apply(self.is_valid_integer), 'error_message'] += f"'{key_to_header_map[column]}' should be a valid integer. "
                    invalid_data.loc[~master_data_df[column].apply(self.is_valid_integer), 'error'] += f"'{key_to_header_map[column]}' should be a valid integer. "
                if is_date:
                    date_pattern = r'\d{4}-\d{2}-\d{2}'
                    is_valid_date = master_data_df[column].astype(str).str.match(date_pattern, na=False)
                    invalid_data.loc[~is_valid_date, 'error_message'] += f"'{key_to_header_map[column]}' should be in 'yyyy-mm-dd' format. "
                    invalid_data.loc[~is_valid_date, 'error'] += f"'{key_to_header_map[column]}' should be in 'yyyy-mm-dd' format. "
                if is_decimal:
                    invalid_data.loc[~pd.to_numeric(master_data_df[column], errors='coerce').notnull(), 'error_message'] += f"'{key_to_header_map[column]}' should be a valid decimal. "
                    invalid_data.loc[~pd.to_numeric(master_data_df[column], errors='coerce').notnull(), 'error'] += f"'{key_to_header_map[column]}' should be a valid decimal. "
                if is_boolean:
                    invalid_data.loc[~master_data_df[column].astype(str).str.upper().isin(['true', 'false', 'TRUE', 'FALSE', '0', '1']), 'error_message'] += f"'{key_to_header_map[column]}' should be (TRUE/FALSE). "
                    invalid_data.loc[~master_data_df[column].astype(str).str.upper().isin(['true', 'false', 'TRUE', 'FALSE', '0', '1']), 'error'] += f"'{key_to_header_map[column]}' should be (TRUE/FALSE). "
            # print(index)
            process.progress = index + 1
            process.save()
        # invalid_data.rename(columns = key_to_header_map, inplace = True)
        return json.dumps(invalid_data.fillna(value='').to_dict(orient='records'))