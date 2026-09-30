from ..validators.commons.index import check_for_all_special_char_and_comma_pipe,customAttributeCheck , description_validator,check_for_comma_pipe,is_input_has_comma,is_input_has_pipe,max_length,is_empty,is_integer,min_value,max_value,greater_than,less_than,is_number,is_valid,check_single_column_duplicate
import json


# Define constants
MAX_CODE_LENGTH = 50
MAX_NAME_LENGTH = 125
MIN_DECIMAL_VAL = 0.00
MAX_DECIMAL_VAL = 100000000
MIN_RLT_VALUE = 3
MIN_RCP_VALUE = 3
MIN_GCP_VALUE = 3
MIN_INT_VALUE = 0
MAX_INT_VALUE = 100000000
MAX_PERMISSION_LENGTH = 200


# Define custom validation functions


class SKUValidations:
    def __init__(self, df):
        self.df = df
        self.df['error'] = ''
        self.df['warning'] = ''

    #perform data validation
    def validation(self,row,index,key_to_header_map,screen_type,validation_rules):
        # print("SELF DF",self.df[self.df['sc']=='ABC'])
        error = ''
        warning = ''
       
        try:
            if('sc' in row.index):
                if(not is_empty(row['sc'])):
                    error += check_for_all_special_char_and_comma_pipe(row['sc'],key_to_header_map['sc'])
                    error += max_length(row['sc'],key_to_header_map['sc'],MAX_CODE_LENGTH)

                    #check if duplicate sc
                    # if(len(self.df[self.df['sc'].str.lower() == row['sc'].lower()]) >1):
                    #     error += '{f} should be unique.'.format(f=key_to_header_map['sc'])
                    error += check_single_column_duplicate(df=self.df,column_name='sc',row_value=row['sc'],key_to_header_map=key_to_header_map)

              
                else:
                    error += '{f} should not be empty.'.format(f=key_to_header_map['sc'])
            
            if(screen_type != 'remove'):

                error += customAttributeCheck(row  , key_to_header_map , MAX_CODE_LENGTH)
                if('sd' in row.index):
                        if(not is_empty(row['sd'])):
                            error += description_validator(row['sd'],key_to_header_map['sd'])
                            error += max_length(row['sd'],key_to_header_map['sd'],MAX_NAME_LENGTH)
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['sd'])
                
                if('ec' in row.index):
                        if(not is_empty(row['ec'])):
                            if(len(is_number(row['ec'],key_to_header_map['ec'])) < 1):
                                if(len(is_integer(row['ec'],key_to_header_map['ec'])) < 1):
                                    error += greater_than(row['ec'],key_to_header_map['ec'],0)
                                    error += max_value(row['ec'],key_to_header_map['ec'],MAX_INT_VALUE)
                                else:
                                    error += '{f} should be Integer.'.format(f=key_to_header_map['ec'])
                            else:
                                error += is_number(row['ec'],key_to_header_map['ec'])
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['ec'])
                
                if('wt' in row.index):
                        if(not is_empty(row['wt'])):
                            if(len(is_number(row['wt'],key_to_header_map['wt'])) < 1):
                                error += greater_than(row['wt'],key_to_header_map['wt'],0)
                                error += max_value(row['wt'],key_to_header_map['wt'],MAX_DECIMAL_VAL)
                            else:
                                error += is_number(row['wt'],key_to_header_map['wt'])  
                        # else:
                        #     error += '{f} should not be empty.'.format(f=key_to_header_map['wt'])
                
                if('vm' in row.index):
                        if(not is_empty(row['vm'])):
                            if(len(is_number(row['vm'],key_to_header_map['vm'])) < 1):
                                error += greater_than(row['vm'],key_to_header_map['vm'],0)
                                error += max_value(row['vm'],key_to_header_map['vm'],MAX_DECIMAL_VAL)
                            else:
                                error += is_number(row['vm'],key_to_header_map['vm'])  
                        # else:
                        #     error += '{f} should not be empty.'.format(f=key_to_header_map['vm'])
                if('SL1' in row.index):
                    if(not is_empty(row['SL1'])):
                        error += max_length(row['SL1'],key_to_header_map['SL1'],MAX_PERMISSION_LENGTH)
                    else:
                        error += '{f} should not be empty.'.format(f=key_to_header_map['SL1'])

                if('SL2' in row.index):
                    if(not is_empty(row['SL2'])):
                        error += max_length(row['SL2'],key_to_header_map['SL2'],MAX_PERMISSION_LENGTH)
                        
                if('SL3' in row.index):
                    if(not is_empty(row['SL3'])):
                        error += max_length(row['SL3'],key_to_header_map['SL3'],MAX_PERMISSION_LENGTH)


            # print("ROW-",index) 
        except Exception as e:
            error = e

        # print(error)  
        row['error'] += str(error)
        row['warning'] += warning  

        if(len(self.df.index) == 1):
            return "[" + json.dumps(row.fillna(value='').to_dict()) + "]"
        if(index == 0):
            return "[" + json.dumps(row.fillna(value='').to_dict()) + ","
        if(index == len(self.df.index)-1):
            return json.dumps(row.fillna(value='').to_dict()) + "]"
        else:
            return json.dumps(row.fillna(value='').to_dict()) + ","