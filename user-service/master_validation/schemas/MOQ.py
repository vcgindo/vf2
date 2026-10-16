from ..validators.commons.index import check_for_all_special_char_and_comma_pipe, check_for_comma_pipe,is_input_has_comma,check_regex,checkForSeparator,is_input_has_pipe,max_length,is_empty,is_integer,min_value,max_value,greater_than,less_than,is_number,is_valid,check_multiple_column_duplicate
import json


# Define constants
MAX_CODE_LENGTH = 50
MAX_NAME_LENGTH = 255
MIN_DECIMAL_VAL = 0.00
MAX_DECIMAL_VAL = 100000000
MIN_RLT_VALUE = 3
MIN_RCP_VALUE = 3
MIN_GCP_VALUE = 3
MAX_INT_VALUE = 100000000


# Define custom validation functions


class MOQValidations:
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
                

            # if('wc' in row.index):
            #     if(not is_empty(row['wc'])):
            #         error += is_input_has_comma(row['wc'],key_to_header_map['wc'])
            #         error += is_input_has_pipe(row['wc'],key_to_header_map['wc'])
            #         error += max_length(row['wc'],key_to_header_map['wc'],MAX_CODE_LENGTH)
            #     else:
            #         error += '{f} should not be empty.'.format(f=key_to_header_map['wc'])
            
            #check is Sku Location Combiation is Unique
            # if(len(self.df[(self.df['sc'].str.lower() == row['sc'].lower()) & (self.df['spc'].str.lower() == row['spc'].lower())]) > 1):
            #     error += '{f},{h} should be unique.'.format(f=key_to_header_map['sc'],h=key_to_header_map['spc'])
            destination_required = screen_type == 'add' and validation_rules.get('moq_destination_required', False)
            duplicate_columns = ['sc', 'spc']
            if destination_required:
                header = key_to_header_map.get('wc', 'Location Code')
                if 'wc' not in row.index or not isinstance(row['wc'], str) or not row['wc'].strip():
                    error += header + ' should not be empty.'
                else:
                    error += check_for_all_special_char_and_comma_pipe(row['wc'], header)
                    error += max_length(row['wc'], header, MAX_CODE_LENGTH)
                    duplicate_columns = ['sc', 'wc', 'spc']
            error += check_multiple_column_duplicate(df=self.df, columns=duplicate_columns, row_values=row, key_to_header_map=key_to_header_map)
            # if('spc' in row.index):
            #     if(not is_empty(row['spc'])):
            #         regexResult = check_regex(row['spc'],key_to_header_map['spc'],"^[a-zA-Z0-9-]*$")
            #         if len(regexResult)==0:
            #             error += max_length(row['spc'],key_to_header_map['spc'],MAX_CODE_LENGTH)
            #         error += regexResult    
            #     else:
            #         error += '{f} should not be empty.'.format(f=key_to_header_map['spc'])

            if('spc' in row.index):
                if(not is_empty(row['spc'])):
                    error += check_for_all_special_char_and_comma_pipe(row['spc'],key_to_header_map['spc'])
                    error += max_length(row['spc'],key_to_header_map['spc'],MAX_CODE_LENGTH)
                else:
                    error += '{f} should not be empty.'.format(f=key_to_header_map['spc'])

            if(screen_type != 'remove'):

                if('mq' in row.index):
                        if(not is_empty(row['mq'])):
                            if(len(is_integer(row['mq'],key_to_header_map['mq'])) < 1):
                                error += min_value(row['mq'],key_to_header_map['mq'],0)
                                error += max_value(row['mq'],key_to_header_map['mq'],MAX_INT_VALUE)
                            else:
                                error += is_integer(row['mq'],key_to_header_map['mq'])
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['mq'])
                            
                
        except Exception as e:
            error = e
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