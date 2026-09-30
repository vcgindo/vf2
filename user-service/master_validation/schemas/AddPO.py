from ..validators.commons.index import check_for_all_special_char_and_comma_pipe, check_for_comma_pipe,is_input_has_comma,is_input_has_pipe,max_length,is_empty,is_integer,min_value,max_value,greater_than,less_than,is_number,is_valid,check_multiple_column_duplicate
import json


# Define constants
MAX_CODE_LENGTH = 50
MAX_NAME_LENGTH = 255
MIN_DECIMAL_VAL = 0.00
MAX_DECIMAL_VAL = 100000000
MIN_RLT_VALUE = 3
MIN_RCP_VALUE = 3
MIN_GCP_VALUE = 3



# Define custom validation functions


class AddPOValidations:
    def __init__(self, df):
        self.df = df
        self.df['error'] = ''
        self.df['warning'] = ''
    
   

    #perform data validation
    def validation(self,row,index,key_to_header_map,screen_type,validation_rules):
        error = ''
        warning = ''

       
        try:
            if('sc' in row.index):
                if(not is_empty(row['sc'])):
                    error += check_for_all_special_char_and_comma_pipe(row['sc'],key_to_header_map['sc'])
                    error += max_length(row['sc'],key_to_header_map['sc'],MAX_CODE_LENGTH)
                else:
                    error += '{f} should not be empty.'.format(f=key_to_header_map['sc'])
                

            if('wc' in row.index):
                if(not is_empty(row['wc'])):
                    error += check_for_all_special_char_and_comma_pipe(row['wc'],key_to_header_map['wc'])
                    error += max_length(row['wc'],key_to_header_map['wc'],MAX_CODE_LENGTH)
                else:
                    error += '{f} should not be empty.'.format(f=key_to_header_map['wc'])
            
            #check is Sku Location Combiation is Unique
            # for next_index in range(index + 1, len(self.df)):
            #     next_row = self.df.iloc[next_index]
            # # Check if both 'sc' and 'wc' are the same between the current row and the next row
            #     if row['sc'] == next_row['sc'] and row['wc'] == next_row['wc']:
            # # Append the error message if a duplicate is found
            #         error += '{f} and {g} should be unique. '.format(f=key_to_header_map['sc'], g=key_to_header_map['wc'])
            error += check_multiple_column_duplicate(df =self.df,columns=['sc', 'wc'], row_values=row,key_to_header_map=key_to_header_map)
                           
            
        except Exception as e:
            error = e

        # print(error)  
        row['error'] += error
        row['warning'] += warning  

        if(len(self.df.index) == 1):
            return "[" + json.dumps(row.fillna(value='').to_dict()) + "]"
        if(index == 0):
            return "[" + json.dumps(row.fillna(value='').to_dict()) + ","
        if(index == len(self.df.index)-1):
            return json.dumps(row.fillna(value='').to_dict()) + "]"
        else:
            return json.dumps(row.fillna(value='').to_dict()) + ","

