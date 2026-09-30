from ..validators.commons.index import check_for_all_special_char_and_comma_pipe, check_for_comma_pipe,is_input_has_comma,checkForSeparator,is_input_has_pipe,check_regex,max_length,is_empty,is_integer,min_value,max_value,greater_than,less_than,is_number,is_valid,check_multiple_column_duplicate
import json


# Define constants
MAX_CODE_LENGTH = 50
MIN_SOB_LENGTH  = 0.00
MAX_SOB_LENGTH = 100.00
MAX_NAME_LENGTH = 255
MIN_DECIMAL_VAL = 0.00
MAX_DECIMAL_VAL = 100000000
MIN_RLT_VALUE = 3
MIN_RCP_VALUE = 3
MIN_GCP_VALUE = 3



# Define custom validation functions


class SOBValidations:
    def __init__(self, df):
        self.df = df
        self.df['error'] = ''
        self.df['warning'] = ''
    
    def supp_code_validator(self,row):
        if row['spc'] == row['wc']:
            return "Supplier code and Location code are same."
        return ''
    
    # def checkForSeparator(self,data,field):
    #     if((',' in data) and ('|' in data)):
    #         return '{f} contains comma and pipe.'.format(f=field)
    #     else:
    #         return ''   

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
            # if(len(self.df[(self.df['sc'].str.lower() == row['sc'].lower()) & (self.df['wc'].str.lower() == row['wc'].lower()) & (self.df['spc'].str.lower() == row['spc'].lower())]) > 1):
            #     error += '{f},{g} and {h} should be unique.'.format(f=key_to_header_map['sc'],g=key_to_header_map['wc'],h=key_to_header_map['spc'])
            error += check_multiple_column_duplicate(df =self.df,columns=['sc','wc','spc'], row_values=row,key_to_header_map=key_to_header_map)

            if('spc' in row.index):
                if(not is_empty(row['spc'])):
                    error += check_for_all_special_char_and_comma_pipe(row['spc'],key_to_header_map['spc'])
                    error += max_length(row['spc'],key_to_header_map['spc'],MAX_CODE_LENGTH)
                else:
                    error += '{f} should not be empty.'.format(f=key_to_header_map['spc'])
            
            if(screen_type != 'remove'):

                if('sb' in row.index):
                        if(not is_empty(row['sb'])):
                            error += self.supp_code_validator(row)
                            if(len(is_integer(row['sb'],key_to_header_map['sb'])) < 1):
                                if float(row['sb']) < MIN_SOB_LENGTH or float(row['sb']) > MAX_SOB_LENGTH:
                                    error += '{f} should be within 0 to 100.'.format(f=key_to_header_map['sb'])
                            else:
                                error += is_integer(row['sb'],key_to_header_map['sb'])  
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['sb'])
            
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

