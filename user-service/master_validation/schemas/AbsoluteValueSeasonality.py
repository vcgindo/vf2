from ..validators.commons.index import check_for_all_special_char_and_comma_pipe, check_for_comma_pipe,is_input_has_comma,is_input_has_pipe,max_length,is_empty,is_integer,min_value,max_value,greater_than,less_than,is_number,is_valid,validate_yyyy_mm_dd,check_multiple_column_duplicate
import json
import pandas as pd
from datetime import datetime
import numpy as np
# Define constants
MAX_CODE_LENGTH = 50
MAX_NAME_LENGTH = 255
MIN_DECIMAL_VAL = 0.00
MAX_DECIMAL_VAL = 100000000
MIN_RLT_VALUE = 3
MIN_RCP_VALUE = 3
MIN_GCP_VALUE = 3
MIN_INT_VALUE = 0
MAX_INT_VALUE = 100000000
MIN_TN_LENGTH = 0.0


# Define custom validation functions


class AbsoluteValueSeasonalityValidations:
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
            # if(len(self.df[(self.df['sc'].str.lower() == row['sc'].lower()) & (self.df['wc'].str.lower() == row['wc'].lower())]) > 1):
            #     error += '{f} and {g} should be unique.'.format(f=key_to_header_map['sc'],g=key_to_header_map['wc'])
            error += check_multiple_column_duplicate(df =self.df,columns=['sc', 'wc'], row_values=row,key_to_header_map=key_to_header_map)
            
            if('sd' in row.index):
                if(not is_empty(row['sd'])):
                    error += max_length(row['sd'],key_to_header_map['sd'],MAX_NAME_LENGTH)
                    data = row['sd'].split(' ')[0]
                    row['sd'] = row['sd'].replace(row['sd'], data)
                    error += validate_yyyy_mm_dd(row['sd'],key_to_header_map['sd'])
                else:
                    error += '{f} should not be empty.'.format(f=key_to_header_map['sd'])

            if('ed' in row.index):
                if(not is_empty(row['ed'])):
                    error += max_length(row['ed'],key_to_header_map['ed'],MAX_NAME_LENGTH)
                    data = row['ed'].split(' ')[0]
                    row['ed'] = row['ed'].replace(row['ed'], data)
                    error += validate_yyyy_mm_dd(row['ed'],key_to_header_map['ed'])
                    if ((not is_empty(row['sd'])) and len(validate_yyyy_mm_dd(row['ed'],key_to_header_map['ed']))<1):
                        start_date = datetime.strptime(row['sd'], "%Y-%m-%d")
                        end_date = datetime.strptime(row['ed'], "%Y-%m-%d")
                        if ((end_date - start_date).days <= 1 and (end_date - start_date).days >= 0):
                            error+='{f} {g} difference Should be minimum 2 days.'.format(f=key_to_header_map['sd'],g=key_to_header_map['ed'])
                        elif ((end_date - start_date).days <0):
                            error+='{g} should be greater than {f}.'.format(f=key_to_header_map['sd'],g=key_to_header_map['ed'])
                else:
                    error+=''

    
            if('tn' in row.index):
                if(not is_empty(row['tn'])):
                    if(len(is_integer(row['tn'],key_to_header_map['tn'])) < 1):
                        error += min_value(row['tn'],key_to_header_map['tn'],MIN_INT_VALUE)
                        error += max_value(row['tn'],key_to_header_map['tn'],MAX_INT_VALUE)
                    else:
                        error += is_integer(row['tn'],key_to_header_map['tn'])    
                else:
                    error += '{f} should not be empty.'.format(f=key_to_header_map['tn'])
                    
                    
            if('bd' in row.index):
                if(not is_empty(row['bd'])):
                    if(len(is_integer(row['bd'],key_to_header_map['bd'])) < 1):
                            error += min_value(row['bd'],key_to_header_map['bd'],MIN_INT_VALUE)
                            error += max_value(row['bd'],key_to_header_map['bd'],MAX_INT_VALUE)
                    else:
                        error += is_integer(row['bd'],key_to_header_map['bd'])  
                # else:
                #     error += '{f} should not be empty.'.format(f=key_to_header_map['bd'])
                           
            
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

