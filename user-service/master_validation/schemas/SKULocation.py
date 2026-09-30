from ..validators.commons.index import check_for_all_special_char_and_comma_pipe, check_for_comma_pipe, description_validator,is_input_has_comma,is_input_has_pipe,max_length,is_empty,is_integer,min_value,max_value,greater_than,less_than,is_number,is_valid , customAttributeCheck,check_multiple_column_duplicate
import json


# Define constants
MAX_CODE_LENGTH = 50
MAX_NAME_LENGTH = 125
MIN_DECIMAL_VAL = 0.00
MAX_DECIMAL_VAL = 10000000
MIN_RLT_VALUE = 3
MIN_RCP_VALUE = 3
MIN_GCP_VALUE = 3
MAX_INT_VALUE = 100000000
MIN_INT_VALUE=0

# Define custom validation functions


class SKULocationValidations:
    def __init__(self, df):
        self.df = df
        self.df['error'] = ''
        self.df['warning'] = ''

    def parent_wh_code_validator(self,row,pwc,wc):
        if row['wc'] == row['pwc']:
            return f"{wc} and {pwc} are the same."
        return ''


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
            
            if(screen_type != 'remove'):

                error += customAttributeCheck(row  , key_to_header_map , MAX_CODE_LENGTH)
                if(screen_type == 'add'):
                        if('sd' in row.index):
                            if(not is_empty(row['sd'])):
                                error += description_validator(row['sd'],key_to_header_map['sd'])
                                error += max_length(row['sd'],key_to_header_map['sd'],MAX_NAME_LENGTH)
                            else:
                                error += '{f} should not be empty.'.format(f=key_to_header_map['sd'])

                        if('wd' in row.index):
                            if(not is_empty(row['wd'])):
                                error += description_validator(row['wd'],key_to_header_map['wd'])
                                error += max_length(row['wd'],key_to_header_map['wd'],MAX_NAME_LENGTH)
                            else:
                                error += '{f} should not be empty.'.format(f=key_to_header_map['wd'])

                        if('n' in row.index):
                            if(not is_empty(row['n'])):
                                error += is_integer(row['n'],key_to_header_map['n'])
                                if(len(is_integer(row['n'],key_to_header_map['n'])) == 0):
                                    error += min_value(row['n'],key_to_header_map['n'],0)
                                    error += max_value(row['n'],key_to_header_map['n'],MAX_INT_VALUE)
                            else:
                                error += '{f} should not be empty.'.format(f=key_to_header_map['n'])
                    
                if('pwc' in row.index):
                        if(not is_empty(row['pwc'])):
                            error += check_for_all_special_char_and_comma_pipe(row['pwc'],key_to_header_map['pwc'])
                            error += max_length(row['pwc'],key_to_header_map['pwc'],MAX_CODE_LENGTH)
                            error += self.parent_wh_code_validator(row,key_to_header_map['pwc'],key_to_header_map['wc'])
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['pwc'])

                    # if('pwc' in row.index):
                    #     if(not is_empty(row['pwc'])):
                    #         error += check_for_all_special_char_and_comma_pipe(row['pwc'],key_to_header_map['pwc'])
                    #         error += max_length(row['pwc'],key_to_header_map['pwc'],MAX_CODE_LENGTH)
                    #     else:
                    #         error += '{f} should not be empty.'.format(f=key_to_header_map['pwc'])

                if('mn' in row.index):
                            if(not is_empty(row['mn'])):
                                error += is_integer(row['mn'],key_to_header_map['mn'])
                                if(len(is_integer(row['mn'],key_to_header_map['mn'])) == 0):
                                    error += min_value(row['mn'],key_to_header_map['mn'],0)
                                    error += max_value(row['mn'],key_to_header_map['mn'],MAX_INT_VALUE)
                            else:
                                error += '{f} should not be empty.'.format(f=key_to_header_map['mn'])
                        
                if('rlt' in row.index):
                        if(not is_empty(row['rlt'])):
                            IntegerCheck = is_integer(row['rlt'],key_to_header_map['rlt'])
                            if (len(IntegerCheck)==0):
                                error+= greater_than(row['rlt'],key_to_header_map['rlt'],0)
                                if len(greater_than(row['rlt'],key_to_header_map['rlt'],0)) == 0:
                                    warning += min_value(row['rlt'],key_to_header_map['rlt'],MIN_RLT_VALUE)

                                error += max_value(row['rlt'],key_to_header_map['rlt'],MAX_INT_VALUE)
                            else:
                                error+=IntegerCheck
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['rlt'])
                    
                if('rcp' in row.index):
                        if(not is_empty(row['rcp'])):
                            IntegerCheck = is_integer(row['rcp'],key_to_header_map['rcp'])
                            if(len(IntegerCheck) == 0 ):
                                error+= greater_than(row['rcp'],key_to_header_map['rcp'],0)
                                if len(greater_than(row['rcp'],key_to_header_map['rcp'],0)) == 0:
                                    warning += min_value(row['rcp'],key_to_header_map['rcp'],MIN_RLT_VALUE)
                                error += max_value(row['rcp'],key_to_header_map['rcp'],MAX_INT_VALUE)
                            else:
                                error+=IntegerCheck
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['rcp'])

                if('gcp' in row.index):
                        if(not is_empty(row['gcp'])):
                            IntegerCheck = is_integer(row['gcp'],key_to_header_map['gcp'])
                            if (len(IntegerCheck)==0):
                                error+= greater_than(row['gcp'],key_to_header_map['gcp'],0)
                                if len(greater_than(row['gcp'],key_to_header_map['gcp'],0)) == 0:
                                    warning += min_value(row['gcp'],key_to_header_map['gcp'],MIN_RLT_VALUE)
                                error += max_value(row['gcp'],key_to_header_map['gcp'],MAX_INT_VALUE)
                            else:
                                error+=IntegerCheck
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['gcp'])

                    # OCP old validation 
                    # if('ocp' in row.index):
                    #     if(not is_empty(row['ocp'])):
                    #         IntegerCheck = is_integer(row['ocp'],key_to_header_map['ocp'])
                    #         if (len(IntegerCheck)==0):
                    #             warning += min_value(row['ocp'],key_to_header_map['ocp'],1)
                    #             error += max_value(row['ocp'],key_to_header_map['ocp'],MAX_INT_VALUE)
                    #         else:
                    #             error+=IntegerCheck
                    #     else:
                    #         error += '{f} should not be empty.'.format(f=key_to_header_map['ocp'])
                    
                if('ocp' in row.index):
                        if(not is_empty(row['ocp'])):
                            IntegerCheck = is_integer(row['ocp'],key_to_header_map['ocp'])
                            if (len(IntegerCheck)==0):
                                error += greater_than(row['ocp'],key_to_header_map['ocp'],0)
                                error += max_value(row['ocp'],key_to_header_map['ocp'],MAX_INT_VALUE)
                            else:
                                error+=IntegerCheck
                        # # OCP can be empty as per new rules
                        # else:
                        #     error += '{f} should not be empty.'.format(f=key_to_header_map['ocp'])
                
                if('moc' in row.index):
                        if(not is_empty(row['moc'])):
                            IntegerCheck = is_integer(row['moc'],key_to_header_map['moc'])
                            if (len(IntegerCheck)==0):
                                error += greater_than(row['moc'],key_to_header_map['moc'],0)
                                error += max_value(row['moc'],key_to_header_map['moc'],MAX_INT_VALUE)
                            else:
                                error+=IntegerCheck
                        # # MOC can be empty as per new rules
                        # else:
                        #     error += '{f} should not be empty.'.format(f=key_to_header_map['moc'])

                    # ps old validation
                    # if('ps' in row.index):
                    #     if(not is_empty(row['ps'])):
                    #         IntegerCheck = is_integer(row['ps'],key_to_header_map['ps'])
                    #         if (len(IntegerCheck)==0):
                    #             warning += min_value(row['ps'],key_to_header_map['ps'],1)
                    #             error += max_value(row['ps'],key_to_header_map['ps'],MAX_INT_VALUE)
                    #         else:
                    #             error+=IntegerCheck
                    #     else:
                    #         error += '{f} should not be empty.'.format(f=key_to_header_map['ps'])
                    
                if('ps' in row.index):
                        if(not is_empty(row['ps'])):
                            IntegerCheck = is_integer(row['ps'],key_to_header_map['ps'])
                            if (len(IntegerCheck)==0):
                                error += greater_than(row['ps'],key_to_header_map['ps'],0)
                                error += max_value(row['ps'],key_to_header_map['ps'],MAX_INT_VALUE)
                            else:
                                error+=IntegerCheck
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['ps'])
                    
                if('st' in row.index):
                        if(not is_empty(row['st'])):
                            if(len(is_number(row['st'],key_to_header_map['st'])) < 1):
                                error += min_value(row['st'],key_to_header_map['st'],MIN_DECIMAL_VAL)
                                error += max_value(row['st'],key_to_header_map['st'],MAX_DECIMAL_VAL)
                            else:
                                error += is_number(row['st'],key_to_header_map['st'])  

                if('spr' in row.index):
                        if(not is_empty(row['spr'])):
                            if(len(is_number(row['spr'],key_to_header_map['spr'])) < 1):
                                IntegerCheck = is_integer(row['spr'],key_to_header_map['spr'])
                                if (len(IntegerCheck)==0):
                                    error += min_value(row['spr'],key_to_header_map['spr'],0)
                                    error += max_value(row['spr'],key_to_header_map['spr'],MAX_INT_VALUE)
                                else:
                                   error+=IntegerCheck
                            else:
                                error += is_number(row['spr'],key_to_header_map['spr'])  
                    
                if('npr' in row.index):
                        if(not is_empty(row['npr'])):
                            IntegerCheck = is_integer(row['npr'],key_to_header_map['npr'])
                            if (len(IntegerCheck)==0):
                                    error += is_number(row['npr'],key_to_header_map['npr'])
                                    error += min_value(row['npr'],key_to_header_map['npr'],0)
                                    error += max_value(row['npr'],key_to_header_map['npr'],MAX_INT_VALUE)
                            else:
                                error+=IntegerCheck

                        
                    # if(not is_empty(row['dst'])):
                    #         if(len(is_number(row['dst'],key_to_header_map['dst'])) < 1):
                    #             error += is_number(row['dst'],key_to_header_map['dst'])
                    #             error += min_value(row['dst'],key_to_header_map['dst'],MIN_DECIMAL_VAL)
                    #             error += max_value(row['dst'],key_to_header_map['dst'],MAX_DECIMAL_VAL)
                    #         else:
                    #             error += is_number(row['dst'],key_to_header_map['dst'])  
                    # else:
                    #     error += '{f} should not be empty.'.format(f=key_to_header_map['dst'])

                if('pt' in row.index):
                        if(not is_empty(row['pt'])):
                            if(len(is_number(row['pt'],key_to_header_map['pt'])) < 1):
                                error += min_value(row['pt'],key_to_header_map['pt'],MIN_DECIMAL_VAL)
                                error += max_value(row['pt'],key_to_header_map['pt'],MAX_DECIMAL_VAL)
                            else:
                                error += is_number(row['pt'],key_to_header_map['pt'])  


                

                    # if(not is_empty(row['dpt'])):
                    #         if(len(is_number(row['dpt'],key_to_header_map['dpt'])) < 1):
                    #             error += is_number(row['dpt'],key_to_header_map['dpt'])
                    #             error += min_value(row['dpt'],key_to_header_map['dpt'],MIN_DECIMAL_VAL)
                    #             error += max_value(row['dpt'],key_to_header_map['dpt'],MAX_DECIMAL_VAL)
                    #         else:
                    #             error += is_number(row['dpt'],key_to_header_map['dpt'])  
                    # else:
                    #     error += '{f} should not be empty.'.format(f=key_to_header_map['dpt'])

                if('frf' in row.index):
                        if(not is_empty(row['frf'])):
                            error += is_valid(str.lower(row['frf']),key_to_header_map['frf'],['fg','rm'])
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['frf']) 

                if('da' in row.index):
                        if(not is_empty(row['da'])):
                            error += is_valid(str.lower(row['da']),key_to_header_map['da'],["yes", "no", "y", "n","1", "0"])
                        else:
                            error += '{f} should not be empty.'.format(f=key_to_header_map['da']) 
                


            # print("ROW-",index) 
        except Exception as e:
            error = e
            # print("ERRRR",e)

        # print("ROWWW",row)  
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
