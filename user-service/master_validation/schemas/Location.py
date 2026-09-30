from ..validators.commons.index import description_validator,customAttributeCheck , check_for_all_special_char_and_comma_pipe,check_for_comma_pipe,checkForSeparator,is_input_only_special_characters,is_input_has_comma,is_input_has_pipe,max_length,is_empty,is_integer,min_value,max_value,greater_than,less_than,is_number,is_valid , check_single_column_duplicate
import json


# Define constants
MAX_CODE_LENGTH = 50
MAX_NAME_LENGTH = 125
MIN_DECIMAL_VAL = 0.00
MAX_DECIMAL_VAL = 100000000
MIN_RLT_VALUE = 3
MIN_RCP_VALUE = 3
MIN_GCP_VALUE = 3
MAX_PERMISSION_LENGTH = 200


# Define custom validation functions


class LocationValidations:
    def __init__(self, df):
        self.df = df
        self.df['error'] = ''
        self.df['warning'] = ''

    #perform data validation
    def validation(self,row,index,key_to_header_map,screen_type,validation_rules):
        error = ''
        warning = ''

        try:
            if('wc' in row.index):
                if(not is_empty(row['wc'])):
                    error += check_for_all_special_char_and_comma_pipe(row['wc'],key_to_header_map['wc'])
                    error += max_length(row['wc'],key_to_header_map['wc'],MAX_CODE_LENGTH)
                    #check if duplicate sc
                    # if(len(self.df[self.df['wc'].str.lower() == row['wc'].lower()])>1):
                    #     error += '{f} should be unique.'.format(f=key_to_header_map['wc'])
                    error += check_single_column_duplicate(df=self.df,column_name='wc',row_value=row['wc'],key_to_header_map=key_to_header_map)
                    
                else:
                    error += '{f} should not be empty.'.format(f=key_to_header_map['wc'])
     
            if(screen_type != 'remove'):

                error += customAttributeCheck(row  , key_to_header_map , MAX_CODE_LENGTH)

                if('wd' in row.index):
                            if(not is_empty(row['wd'])):
                                error += description_validator(row['wd'],key_to_header_map['wd'])
                                error += max_length(row['wd'],key_to_header_map['wd'],MAX_NAME_LENGTH)
                            else:
                                error += '{f} should not be empty.'.format(f=key_to_header_map['wd'])
                    
                if('l' in row.index):
                            if(not is_empty(row['l'])):
                                error += check_for_all_special_char_and_comma_pipe(row['l'],key_to_header_map['l'])
                                error += max_length(row['l'],key_to_header_map['l'],MAX_CODE_LENGTH)
                            # else:
                            #     error += '{f} should not be empty.'.format(f=key_to_header_map['l'])

                if('lc' in row.index):
                        if(not is_empty(row['lc'])):
                            error += check_for_all_special_char_and_comma_pipe(row['lc'],key_to_header_map['lc'])
                            error += max_length(row['lc'],key_to_header_map['lc'],MAX_CODE_LENGTH)
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['lc'])

                if('LL1' in row.index):
                    if(not is_empty(row['LL1'])):
                        error += max_length(row['LL1'],key_to_header_map['LL1'],MAX_PERMISSION_LENGTH)
                    else:
                        error += '{f} should not be empty.'.format(f=key_to_header_map['LL1'])

                if('LL2' in row.index):
                    if(not is_empty(row['LL2'])):
                            error += max_length(row['LL2'],key_to_header_map['LL2'],MAX_PERMISSION_LENGTH)

                if('LL3' in row.index):
                    if(not is_empty(row['LL3'])):            
                            error += max_length(row['LL3'],key_to_header_map['LL3'],MAX_PERMISSION_LENGTH)

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

